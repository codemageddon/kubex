from __future__ import annotations

import logging
import netrc
import os
import ssl
import warnings
from contextlib import AbstractAsyncContextManager, contextmanager, nullcontext
from types import EllipsisType
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    ContextManager,
    Iterator,
    NoReturn,
    Sequence,
    cast,
)
from urllib.parse import urlparse

import anyio
import httpx

from kubex.client._common import (
    WS_PING_INTERVAL_SECONDS,
    LineSplitter,
    describe_exception,
    emit_api_warnings,
)
from kubex.client.options import ClientOptions, resolve_ws_max_message_size
from kubex.client.websocket import WebSocketConnection
from kubex.configuration import ClientConfiguration
from kubex.core.exceptions import (
    ConfigurationError,
    KubexClientException,
    KubexConnectionError,
    KubexException,
    KubexTimeoutError,
)
from kubex.core.params import Timeout, TimeoutTypes
from kubex.core.request import Request
from kubex.core.response import HeadersWrapper, Response

from .client import (
    BaseClient,
    handle_request_error,
)

if TYPE_CHECKING:
    from httpx_ws import AsyncWebSocketSession


def _to_httpx_headers(pairs: list[tuple[str, str]]) -> httpx.Headers:
    """Build httpx headers, sending non-ASCII values as UTF-8 bytes.

    httpx encodes `str` header values as ASCII and raises on anything else
    (e.g. a non-ASCII `Impersonate-User`); aiohttp and client-go send UTF-8.
    """
    return httpx.Headers([(name.encode(), value.encode()) for name, value in pairs])


def _to_httpx_timeout(timeout: Timeout | None) -> httpx.Timeout:
    """Translate a ``Timeout`` (or explicit ``None``) to an ``httpx.Timeout``."""
    if timeout is None:
        return httpx.Timeout(None)
    return httpx.Timeout(
        timeout.total,
        connect=timeout.connect if timeout.connect is not None else timeout.total,
        read=timeout.read if timeout.read is not None else timeout.total,
        write=timeout.write if timeout.write is not None else timeout.total,
        pool=timeout.pool if timeout.pool is not None else timeout.total,
    )


def _total_seconds(timeout: TimeoutTypes | EllipsisType) -> float | None:
    if isinstance(timeout, Timeout):
        return timeout.total
    if isinstance(timeout, (int, float)):
        return float(timeout)
    return None


# httpx's own ``DEFAULT_LIMITS``; ``httpx.Limits()`` with a field omitted means
# "unlimited" for that field, not "default".
_HTTPX_DEFAULT_LIMITS: dict[str, Any] = {
    "max_connections": 100,
    "max_keepalive_connections": 20,
    "keepalive_expiry": 5.0,
}


def _build_httpx_limits(options: ClientOptions) -> dict[str, Any]:
    """Build ``httpx.Limits`` kwargs from the pool/keep-alive options.

    Returns an empty dict when all three fields are still ``...`` so that the
    caller can skip creating an ``httpx.Limits`` object entirely (letting httpx
    apply its own full default ``Limits``). Otherwise fields left at ``...``
    are filled with httpx's defaults.
    """
    kw: dict[str, Any] = {}

    pool_size = options.pool_size
    if pool_size is None:
        kw["max_connections"] = None
    elif not isinstance(pool_size, EllipsisType):
        kw["max_connections"] = pool_size

    if not options.keep_alive:
        kw["max_keepalive_connections"] = 0

    keep_alive_timeout = options.keep_alive_timeout
    if keep_alive_timeout is None:
        kw["keepalive_expiry"] = None
    elif not isinstance(keep_alive_timeout, EllipsisType):
        kw["keepalive_expiry"] = keep_alive_timeout

    if not kw:
        return kw
    return {**_HTTPX_DEFAULT_LIMITS, **kw}


def _build_httpx_proxy_kwargs(
    proxy: str | dict[str, str] | None,
    verify: ssl.SSLContext | bool,
    limits: httpx.Limits | None = None,
) -> dict[str, Any]:
    """Build proxy-related kwargs for ``httpx.AsyncClient``.

    On httpx >= 0.27.2, ``AsyncHTTPTransport`` accepts ``verify=ssl.SSLContext``
    directly (verified against the 0.27.2 source), so the existing ssl_context
    (which may carry custom CA, client cert, or insecure-skip-verify settings)
    is forwarded to each per-scheme transport entry in the dict case.

    When ``limits`` is provided it is applied to each per-scheme transport so
    that pool-size and keep-alive settings take effect for proxied traffic too.
    Without this, mounted transports ignore the client-level ``Limits`` object.
    """
    if proxy is None:
        return {}
    if isinstance(proxy, str):
        return {"proxy": proxy}
    transport_kw: dict[str, Any] = {"verify": verify}
    if limits is not None:
        transport_kw["limits"] = limits
    return {
        "mounts": {
            f"{scheme}://": httpx.AsyncHTTPTransport(proxy=url, **transport_kw)
            for scheme, url in proxy.items()
        }
    }


_logger = logging.getLogger("kubex.client.httpx")


@contextmanager
def _translate_httpx_errors(action: str) -> Iterator[None]:
    """Re-raise httpx transport errors (and deadline expiry) as kubex exceptions.

    Only ``Exception`` subclasses are caught, so cancellation and
    ``GeneratorExit`` always pass through untouched.
    """
    try:
        yield
    except KubexException:
        raise
    except (httpx.TimeoutException, TimeoutError) as exc:
        raise KubexTimeoutError(f"{action} timed out") from exc
    except httpx.TransportError as exc:
        raise KubexConnectionError(
            f"{action} failed: {describe_exception(exc)}"
        ) from exc
    except httpx.HTTPError as exc:
        raise KubexClientException(
            f"{action} failed: {describe_exception(exc)}"
        ) from exc


async def _buffer_rejected_upgrade_body(response: httpx.Response) -> None:
    """Read the body of a rejected WebSocket upgrade while it is still open.

    httpx-ws closes the response before raising ``WebSocketUpgradeError``, so
    this response hook is the only chance to keep the API server's ``Status``
    explaining a 403/404 on exec/attach/portforward.
    """
    if (
        response.status_code >= 400
        and response.request.headers.get("upgrade", "").lower() == "websocket"
    ):
        try:
            await response.aread()
        except httpx.HTTPError:
            pass


def _raise_for_rejected_upgrade(response: httpx.Response) -> NoReturn:
    status = response.status_code
    if status >= 400:
        try:
            body = response.content
        except httpx.ResponseNotRead:
            body = b""
        handle_request_error(
            Response(
                content=body,
                headers=HeadersWrapper(response.headers),
                status_code=status,
            )
        )
    raise KubexClientException(
        f"WebSocket handshake failed: unexpected HTTP status {status}"
    )


def _getenv_icase(name: str) -> tuple[str | None, str]:
    """Case-insensitive env var lookup: lowercase > uppercase > mixed-case.

    Returns (matched_key, value) or (None, "") if not present at any case variant.
    A higher-priority set-but-empty value suppresses lower-priority non-empty values,
    preserving the curl/urllib convention that ``https_proxy=""`` suppresses
    ``HTTPS_PROXY``.

    Always returns the *actual* key stored in ``os.environ``, not the normalised
    lookup form.  This is critical on Windows where ``os.environ`` is
    case-insensitive: a containment check like ``"http_proxy" in os.environ``
    returns ``True`` when only ``HTTP_PROXY`` is stored, and the subsequent
    ``os.environ["http_proxy"]`` call returns the value but the caller would
    record the synthetic lowercase key — breaking the HTTPOXY guard which
    compares ``found_key == "HTTP_PROXY"``.
    """
    lc = name.lower()
    uc = name.upper()
    lc_match: tuple[str, str] | None = None
    uc_match: tuple[str, str] | None = None
    mc_match: tuple[str, str] | None = None
    for k, v in os.environ.items():
        if k == lc:
            lc_match = (k, v)
        elif k == uc:
            uc_match = (k, v)
        elif k.lower() == lc:
            mc_match = (k, v)
    if lc_match is not None:
        return lc_match
    if uc_match is not None:
        return uc_match
    if mc_match is not None:
        return mc_match
    return None, ""


def _host_matches_no_proxy(host: str, no_proxy: str) -> bool:
    """NO_PROXY host matching compatible with Python stdlib / aiohttp.

    Entries are comma-separated and whitespace-trimmed. Matching rules:

    - ``*`` matches every host.
    - A leading-dot entry (e.g. ``.example.com``) matches the exact domain
      AND any subdomain — ``.example.com`` matches both ``example.com`` and
      ``api.example.com``, consistent with curl and Python's urllib.
    - A bare-domain entry (e.g. ``example.com``) matches the exact host and
      any subdomain.
    - Port qualifiers in entries (e.g. ``example.com:6443``) are NOT
      supported and will never match — consistent with Python stdlib and
      aiohttp behavior. Use a bare hostname entry (``example.com``) instead.
    - Bracketed IPv6 entries (e.g. ``[::1]``) are NOT supported — use the
      bare IPv6 address (``::1``) instead. Consistent with Python stdlib and
      aiohttp, which do not strip brackets before matching.
    - An IP literal matches only the exact IP; CIDR notation is NOT supported.
    - Comparison is case-insensitive.
    """
    host = host.lower()
    for raw_entry in (e.strip().lower() for e in no_proxy.split(",")):
        if not raw_entry:
            continue
        if raw_entry == "*":
            return True
        # Strip leading dot so that .example.com and example.com both match the
        # domain itself and its subdomains (curl / Python stdlib semantics).
        bare = raw_entry.lstrip(".")
        if host == bare or host.endswith("." + bare):
            return True
    return False


def _resolve_env_proxy_with_netrc(base_url: str) -> dict[str, Any]:
    """Resolve env-based proxy URL and netrc credentials for the httpx backend.

    Returns a kwargs dict to be ``.update()``'d into ``httpx.AsyncClient``
    constructor kwargs:

    - ``{}`` if no env proxy var is set, or NO_PROXY matches the base url host.
    - ``{"proxy": "<url-str>"}`` if the env proxy URL has embedded ``user:pass``
      or netrc has no matching entry.
    - ``{"proxy": httpx.Proxy(url=..., auth=(login, password))}`` if the env
      proxy URL has no creds AND netrc has a ``machine`` entry for the proxy
      host.

    Netrc read failures are caught and silently downgraded to "no creds" with
    the proxy URL still applied. Failures are logged at DEBUG level.
    """
    parsed_base = urlparse(base_url)
    base_host = (parsed_base.hostname or "").lower()
    scheme = (parsed_base.scheme or "").lower()

    if scheme == "https":
        candidates = ["https_proxy", "all_proxy"]
    else:
        candidates = ["http_proxy", "all_proxy"]

    proxy_url: str | None = None
    for target in candidates:
        found_key, found_val = _getenv_icase(target)
        if found_key is None:
            continue
        # CGI safeguard (CVE-2016-1000110 / HTTPOXY): skip exact uppercase
        # HTTP_PROXY in CGI context to prevent header injection.  Only the
        # exact uppercase form can be injected by a CGI server (RFC 3875
        # uppercases header names); lowercase and mixed-case variants are
        # user-set and are allowed.  Applied on all platforms (including
        # Windows) to match stdlib / aiohttp behavior.
        if found_key == "HTTP_PROXY" and "REQUEST_METHOD" in os.environ:
            continue
        if found_val:
            proxy_url = found_val
            break
        # Empty value at the winning priority level suppresses this candidate
        # but allows fallback to the next entry (e.g. ALL_PROXY).

    if proxy_url is None:
        return {}

    # Case-insensitive NO_PROXY lookup with the same priority rule.
    no_proxy_key, no_proxy_val = _getenv_icase("no_proxy")
    no_proxy = no_proxy_val if no_proxy_key is not None else ""
    if no_proxy and _host_matches_no_proxy(base_host, no_proxy):
        return {}

    parsed_proxy = urlparse(proxy_url)
    if parsed_proxy.username or parsed_proxy.password:
        return {"proxy": proxy_url}

    proxy_host = parsed_proxy.hostname or ""
    netrc_path = os.environ.get("NETRC") or None
    try:
        rc = netrc.netrc(netrc_path)
        creds = rc.authenticators(proxy_host)
        if creds is not None:
            login, _, password = creds
            if login is not None:
                return {
                    "proxy": httpx.Proxy(url=proxy_url, auth=(login, password or ""))
                }
    except netrc.NetrcParseError as exc:
        # Not ``exc`` itself: its message quotes the offending token, which
        # may be (part of) a password.
        _logger.debug(
            "Failed to parse netrc %s at line %s; ignoring it for proxy credentials",
            exc.filename,
            exc.lineno,
        )
    except OSError as exc:
        _logger.debug("Failed to read netrc for proxy credentials: %s", exc)

    return {"proxy": proxy_url}


class HttpxClient(BaseClient):
    def __init__(
        self,
        configuration: ClientConfiguration,
        options: ClientOptions | None = None,
    ) -> None:
        super().__init__(configuration, options)

    def _create_inner_client(self) -> httpx.AsyncClient:
        cafile = (
            str(self.configuration.server_ca_file)
            if self.configuration.server_ca_file
            else None
        )
        client_cert = self.configuration.client_cert
        needs_custom_ssl = bool(
            cafile or self.configuration.insecure_skip_tls_verify or client_cert
        )
        _verify: ssl.SSLContext | bool
        if needs_custom_ssl:
            ssl_context = ssl.create_default_context(cafile=cafile)
            if client_cert is not None:
                if isinstance(client_cert, tuple):
                    ssl_context.load_cert_chain(
                        certfile=client_cert[0], keyfile=client_cert[1]
                    )
                else:
                    ssl_context.load_cert_chain(certfile=client_cert)
            if self.configuration.insecure_skip_tls_verify:
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
            _verify = ssl_context
        else:
            # No custom TLS settings — let httpx use its default trust bundle
            # (certifi), which is consistent with the pre-ClientOptions behavior.
            _verify = True

        kwargs: dict[str, Any] = {
            "base_url": str(self.configuration.base_url),
            "verify": _verify,
            "event_hooks": {"response": [_buffer_rejected_upgrade_body]},
        }
        configured_timeout = self.options.timeout
        if configured_timeout is not Ellipsis:
            kwargs["timeout"] = _to_httpx_timeout(
                cast("Timeout | None", configured_timeout)
            )

        limits_kw = _build_httpx_limits(self.options)
        limits = httpx.Limits(**limits_kw) if limits_kw else None
        if limits is not None:
            kwargs["limits"] = limits

        if self.options.trust_env and self.options.proxy is not None:
            warnings.warn(
                "ClientOptions.proxy is set; env-based proxy variables "
                "(HTTP_PROXY/HTTPS_PROXY/NO_PROXY) are ignored when "
                "trust_env=True coexists with an explicit proxy.",
                UserWarning,
                stacklevel=3,
            )
            kwargs["trust_env"] = False
            # Passing trust_env=False to httpx also suppresses SSL_CERT_FILE /
            # SSL_CERT_DIR. When no custom CA is configured via kubeconfig,
            # apply these env vars manually so env-provided CA bundles are not
            # silently downgraded to certifi.
            if not needs_custom_ssl:
                ssl_cert_file = os.environ.get("SSL_CERT_FILE")
                ssl_cert_dir = os.environ.get("SSL_CERT_DIR")
                if ssl_cert_file or ssl_cert_dir:
                    env_ssl_ctx = ssl.create_default_context(
                        cafile=ssl_cert_file, capath=ssl_cert_dir
                    )
                    _verify = env_ssl_ctx
                    kwargs["verify"] = env_ssl_ctx
        elif self.options.trust_env:
            kwargs["trust_env"] = True
            kwargs.update(
                _resolve_env_proxy_with_netrc(str(self.configuration.base_url))
            )
        else:
            kwargs["trust_env"] = False

        kwargs.update(_build_httpx_proxy_kwargs(self.options.proxy, _verify, limits))

        # An env proxy that applies to the server is already in kwargs["proxy"]
        # (see _resolve_env_proxy_with_netrc), so NO_PROXY bypasses don't warn.
        if self.configuration.tls_server_name and (
            "proxy" in kwargs or "mounts" in kwargs
        ):
            # httpcore's CONNECT tunnel verifies against the URL host and
            # ignores the `sni_hostname` extension.
            warnings.warn(
                "tls_server_name is not applied by the httpx backend when "
                "connecting through an HTTP proxy; certificate verification "
                "uses the server URL's host. Use the aiohttp backend or "
                "connect without a proxy.",
                UserWarning,
                stacklevel=3,
            )

        if not isinstance(self.options.buffer_size, EllipsisType):
            warnings.warn(
                "ClientOptions.buffer_size is set but httpx has no equivalent "
                "buffer-size knob; the value is ignored on the httpx backend.",
                UserWarning,
                stacklevel=3,
            )

        if not isinstance(self.options.pool_size_per_host, EllipsisType):
            warnings.warn(
                "ClientOptions.pool_size_per_host is set but httpx has no "
                "per-host pool limit; the value is ignored on the httpx backend.",
                UserWarning,
                stacklevel=3,
            )

        if self.options.ws_max_message_size is None:
            warnings.warn(
                "ClientOptions.ws_max_message_size=None is not supported on the "
                "httpx backend; falls back to httpx-ws default (65536 bytes). "
                "The value is ignored.",
                UserWarning,
                stacklevel=3,
            )

        return httpx.AsyncClient(**kwargs)

    async def request(self, request: Request) -> Response:
        headers = _to_httpx_headers(await self._request_headers(request))
        extra = self._transport_kwargs()
        if request.timeout is not Ellipsis:
            extra["timeout"] = _to_httpx_timeout(request.timeout)
        # httpx timeouts are per phase; enforce ``total`` as a real wall-clock
        # bound so a numeric timeout means the same thing on both backends.
        total = _total_seconds(
            self.options.timeout if request.timeout is Ellipsis else request.timeout
        )
        deadline: ContextManager[Any] = (
            anyio.fail_after(total) if total is not None else nullcontext()
        )
        with _translate_httpx_errors(f"{request.method} {request.url}"):
            with deadline:
                _response = await self._inner_client.request(
                    method=request.method,
                    url=request.url,
                    params=request.query_params,
                    content=request.body,
                    headers=headers,
                    **extra,
                )
        status = _response.status_code
        response = Response(
            status_code=status,
            headers=HeadersWrapper(_response.headers),
            content=_response.content,
        )
        if self.options.log_api_warnings:
            emit_api_warnings(_response.headers.get_list("warning"))
        if 400 <= status < 600:
            handle_request_error(response)
        return response

    def _stream_timeout(self) -> httpx.Timeout:
        """Client timeout with read disabled: watches and log follows idle legitimately."""
        base: httpx.Timeout = self._inner_client.timeout
        return httpx.Timeout(
            None, connect=base.connect, write=base.write, pool=base.pool
        )

    async def stream_lines(self, request: Request) -> AsyncGenerator[str, None]:
        headers = _to_httpx_headers(await self._request_headers(request))
        extra = self._transport_kwargs()
        extra["timeout"] = (
            self._stream_timeout()
            if request.timeout is Ellipsis
            else _to_httpx_timeout(request.timeout)
        )
        with _translate_httpx_errors(f"{request.method} {request.url}"):
            async with self._inner_client.stream(
                method=request.method,
                url=request.url,
                params=request.query_params,
                content=request.body,
                headers=headers,
                **extra,
            ) as _response:
                status = _response.status_code
                if 400 <= status < 600:
                    response = Response(
                        status_code=status,
                        headers=HeadersWrapper(_response.headers),
                        content=await _response.aread(),
                    )
                    handle_request_error(response)
                if self.options.log_api_warnings:
                    emit_api_warnings(_response.headers.get_list("warning"))
                splitter = LineSplitter()
                async for chunk in _response.aiter_bytes():
                    for line in splitter.feed(chunk):
                        yield line
                if (tail := splitter.flush()) is not None:
                    yield tail

    def _transport_kwargs(self) -> dict[str, Any]:
        if self.configuration.tls_server_name:
            return {"extensions": {"sni_hostname": self.configuration.tls_server_name}}
        return {}

    async def close(self) -> None:
        await self._inner_client.aclose()

    async def connect_websocket(
        self,
        request: Request,
        subprotocols: Sequence[str],
    ) -> WebSocketConnection:
        try:
            import httpx_ws
        except ImportError as exc:
            raise ConfigurationError(
                "httpx-ws is required for WebSocket connections; "
                "install kubex[httpx-ws]"
            ) from exc

        # httpx-ws calls ``headers.update()``; ``httpx.Headers`` keeps repeated
        # names (e.g. several ``Impersonate-Group``).
        headers = _to_httpx_headers(await self._request_headers(request))

        params: Any = (
            request.query_param_pairs
            if request.query_param_pairs is not None
            else request.query_params
        )
        extra = self._transport_kwargs()
        if request.timeout is not Ellipsis:
            # Forwarded as-is to httpx.stream() during the WebSocket upgrade;
            # bounds the handshake but not the streaming exec session itself.
            # No outer ``fail_after`` here: httpx-ws opens a task group inside
            # ``__aenter__``, which must not outlive an enclosing cancel scope.
            extra["timeout"] = _to_httpx_timeout(request.timeout)
        ws_opt = self.options.ws_max_message_size
        if ws_opt is not None:
            extra["max_message_size_bytes"] = resolve_ws_max_message_size(ws_opt)
        cm: AbstractAsyncContextManager[AsyncWebSocketSession] = httpx_ws.aconnect_ws(
            request.url,
            client=self._inner_client,
            subprotocols=list(subprotocols) if subprotocols else None,
            headers=headers,
            params=params,
            # Keep pinging (idle load balancers) but never enforce a pong
            # deadline: httpx-ws only processes pongs while kubex reads, so a
            # consumer applying backpressure would otherwise be disconnected
            # with 1011 "Keepalive ping timeout".
            keepalive_ping_interval_seconds=WS_PING_INTERVAL_SECONDS,
            keepalive_ping_timeout_seconds=None,
            **extra,
        )

        try:
            session = await cm.__aenter__()
        except httpx_ws.WebSocketUpgradeError as exc:
            _raise_for_rejected_upgrade(exc.response)
        except httpx.TimeoutException as exc:
            raise KubexTimeoutError("WebSocket handshake timed out") from exc
        except httpx.TransportError as exc:
            # ``ConnectError``, ``NetworkError``, TLS / DNS / proxy errors, etc.
            raise KubexConnectionError(
                f"WebSocket connection failed: {describe_exception(exc)}"
            ) from exc
        except httpx.HTTPError as exc:
            raise KubexClientException(
                f"WebSocket connection failed: {describe_exception(exc)}"
            ) from exc

        if subprotocols and session.subprotocol is None:
            # Suppress any cleanup error so the descriptive subprotocol
            # mismatch is what the caller sees, rather than a transport
            # close failure masking the real diagnosis. ``except Exception``
            # (not ``BaseException``) so a ``Cancelled`` raised during the
            # close propagates and cooperative cancellation is not dropped.
            try:
                await cm.__aexit__(None, None, None)
            except Exception:
                pass
            raise KubexClientException(
                "Server did not negotiate any of the requested subprotocols: "
                f"{list(subprotocols)}"
            )

        return HttpxWebSocketConnection(cm, session)


class HttpxWebSocketConnection(WebSocketConnection):
    """Adapter wrapping an :class:`httpx_ws.AsyncWebSocketSession`."""

    def __init__(
        self,
        cm: AbstractAsyncContextManager[AsyncWebSocketSession],
        session: AsyncWebSocketSession,
    ) -> None:
        self._cm = cm
        self._session = session
        # ``_eof`` short-circuits further ``receive_bytes()`` calls once the
        # peer closes or the transport breaks. ``_cm_exited`` guards the
        # underlying ``httpx_ws`` context manager so its ``__aexit__`` runs
        # exactly once — the EOF path must not skip releasing the HTTP stream.
        self._eof = False
        self._cm_exited = False

    @property
    def closed(self) -> bool:
        return self._eof or self._cm_exited

    @property
    def negotiated_subprotocol(self) -> str | None:
        proto = self._session.subprotocol
        return proto if proto is None else str(proto)

    async def send_bytes(self, data: bytes) -> None:
        from anyio import ClosedResourceError

        from httpx_ws import HTTPXWSException

        try:
            await self._session.send_bytes(data)
        except HTTPXWSException as exc:
            # Covers ``WebSocketDisconnect`` (peer closed mid-send) and
            # ``WebSocketNetworkError`` (transport loss). Normalize for
            # symmetry with the receive path so callers writing stdin or
            # resize frames see ``KubexClientException`` rather than raw
            # backend-specific exception types.
            raise KubexClientException(f"WebSocket send failed: {exc}") from exc
        except ClosedResourceError as exc:
            raise KubexClientException(
                "WebSocket send failed: connection closed"
            ) from exc
        except KubexException:
            raise
        except Exception as exc:
            # e.g. wsproto ``LocalProtocolError`` once the peer started closing.
            raise KubexClientException(
                f"WebSocket send failed: {describe_exception(exc)}"
            ) from exc

    async def receive_bytes(self) -> bytes:
        from anyio import ClosedResourceError

        from httpx_ws import (
            WebSocketDisconnect,
            WebSocketInvalidTypeReceived,
            WebSocketNetworkError,
        )

        if self._eof or self._cm_exited:
            raise StopAsyncIteration
        try:
            return await self._session.receive_bytes()
        except WebSocketInvalidTypeReceived as exc:
            # The K8s exec/attach/port-forward subresources only ever send
            # binary frames over v5.channel.k8s.io. A text frame is a protocol
            # violation; surface it as a normalized client exception rather
            # than leaking the backend-specific exception type to callers.
            raise KubexClientException(
                "WebSocket received unexpected non-binary frame"
            ) from exc
        except WebSocketDisconnect as exc:
            self._eof = True
            # 1000 (NORMAL_CLOSURE), 1001 (GOING_AWAY) and 1005 (NO_STATUS_RCVD,
            # i.e. peer close frame without a status code — surfaced by
            # httpx-ws/wsproto for a code-less close) are clean EOF; any
            # other close code indicates an abnormal termination.
            if exc.code in (1000, 1001, 1005):
                raise StopAsyncIteration from exc
            raise KubexClientException(
                f"WebSocket closed abnormally (code={exc.code}, reason={exc.reason!r})"
            ) from exc
        except WebSocketNetworkError as exc:
            self._eof = True
            raise KubexClientException(f"WebSocket network error: {exc}") from exc
        except ClosedResourceError as exc:
            self._eof = True
            raise StopAsyncIteration from exc
        except (KubexException, StopAsyncIteration):
            raise
        except Exception as exc:
            self._eof = True
            raise KubexClientException(
                f"WebSocket receive failed: {describe_exception(exc)}"
            ) from exc

    async def close(self) -> None:
        from httpx_ws import HTTPXWSException

        if self._cm_exited:
            return
        self._cm_exited = True
        self._eof = True
        try:
            await self._cm.__aexit__(None, None, None)
        except HTTPXWSException:
            pass
        except KubexException:
            raise
        except Exception as exc:
            raise KubexClientException(
                f"WebSocket close failed: {describe_exception(exc)}"
            ) from exc
