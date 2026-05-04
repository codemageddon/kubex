from __future__ import annotations

import ssl
import warnings
from contextlib import AbstractAsyncContextManager
from types import EllipsisType
from typing import TYPE_CHECKING, Any, AsyncGenerator, Sequence, cast

import httpx

from kubex.client.options import ClientOptions, resolve_ws_max_message_size
from kubex.client.websocket import WebSocketConnection
from kubex.configuration import ClientConfiguration
from kubex.core.exceptions import ConfgiurationError, KubexClientException
from kubex.core.params import Timeout
from kubex.core.request import Request
from kubex.core.response import HeadersWrapper, Response

from .client import (
    BaseClient,
    handle_request_error,
)

if TYPE_CHECKING:
    from httpx_ws import AsyncWebSocketSession


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


def _build_httpx_limits(options: ClientOptions) -> dict[str, Any]:
    """Collect only the explicitly-set pool/keep-alive fields into a Limits kwargs dict.

    Returns an empty dict when all three fields are still ``...`` so that the
    caller can skip creating an ``httpx.Limits`` object entirely (letting httpx
    apply its own full default ``Limits``).
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

    return kw


def _build_httpx_proxy_kwargs(
    proxy: str | dict[str, str] | None,
    ssl_context: ssl.SSLContext,
) -> dict[str, Any]:
    """Build proxy-related kwargs for ``httpx.AsyncClient``.

    On httpx >= 0.27.2, ``AsyncHTTPTransport`` accepts ``verify=ssl.SSLContext``
    directly (verified against the 0.27.2 source), so the existing ssl_context
    (which may carry custom CA, client cert, or insecure-skip-verify settings)
    is forwarded to each per-scheme transport entry in the dict case.
    """
    if proxy is None:
        return {}
    if isinstance(proxy, str):
        return {"proxy": proxy}
    return {
        "mounts": {
            f"{scheme}://": httpx.AsyncHTTPTransport(proxy=url, verify=ssl_context)
            for scheme, url in proxy.items()
        }
    }


class HttpxClient(BaseClient):
    def __init__(
        self,
        configuration: ClientConfiguration,
        options: ClientOptions | None = None,
    ) -> None:
        super().__init__(configuration, options)

    @property
    def configuration(self) -> ClientConfiguration:
        return self._configuration

    def _get_headers(self) -> dict[str, str]:
        if self.configuration.token is None:
            return {}
        return {"Authorization": f"Bearer {self.configuration.token}"}

    def _create_inner_client(self) -> httpx.AsyncClient:
        cafile = (
            str(self.configuration.server_ca_file)
            if self.configuration.server_ca_file
            else None
        )
        ssl_context = ssl.create_default_context(cafile=cafile)
        if (client_cert := self.configuration.client_cert) is not None:
            if isinstance(client_cert, tuple):
                ssl_context.load_cert_chain(
                    certfile=client_cert[0], keyfile=client_cert[1]
                )
            else:
                ssl_context.load_cert_chain(certfile=client_cert)
        if self.configuration.insecure_skip_tls_verify:
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
        _verify: ssl.SSLContext = ssl_context

        kwargs: dict[str, Any] = {
            "base_url": str(self.configuration.base_url),
            "verify": _verify,
        }
        configured_timeout = self.options.timeout
        if configured_timeout is not Ellipsis:
            kwargs["timeout"] = _to_httpx_timeout(
                cast("Timeout | None", configured_timeout)
            )

        limits_kw = _build_httpx_limits(self.options)
        if limits_kw:
            kwargs["limits"] = httpx.Limits(**limits_kw)

        kwargs.update(_build_httpx_proxy_kwargs(self.options.proxy, ssl_context))

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
        headers = self._get_headers()
        if request.headers:
            headers.update(request.headers)
        extra: dict[str, Any] = {}
        if request.timeout is not Ellipsis:
            extra["timeout"] = _to_httpx_timeout(request.timeout)
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
        if self.options.log_api_warnings and (
            api_warnings := _response.headers.get("warning")
        ):
            for warning in api_warnings.split(","):
                warnings.warn(
                    f"API Warning: {warning.strip()}", UserWarning, stacklevel=2
                )
        if 400 <= status < 600:
            handle_request_error(response)
        return response

    async def stream_lines(self, request: Request) -> AsyncGenerator[str, None]:
        headers = self._get_headers()
        if request.headers:
            headers.update(request.headers)
        extra: dict[str, Any] = {}
        if request.timeout is not Ellipsis:
            extra["timeout"] = _to_httpx_timeout(request.timeout)
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
            if self.options.log_api_warnings and (
                api_warnings := _response.headers.get("warning")
            ):
                for warning in api_warnings.split(","):
                    warnings.warn(
                        f"API Warning: {warning.strip()}",
                        UserWarning,
                        stacklevel=2,
                    )
            async for line in _response.aiter_lines():
                yield line

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
            raise ConfgiurationError(
                "httpx-ws is required for WebSocket connections; "
                "install kubex[httpx-ws]"
            ) from exc

        headers = self._get_headers()
        if request.headers:
            headers.update(request.headers)

        params: Any = (
            request.query_param_pairs
            if request.query_param_pairs is not None
            else request.query_params
        )
        extra: dict[str, Any] = {}
        if request.timeout is not Ellipsis:
            # Forwarded as-is to httpx.stream() during the WebSocket upgrade;
            # bounds the handshake but not the streaming exec session itself.
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
            **extra,
        )

        try:
            session = await cm.__aenter__()
        except httpx_ws.WebSocketUpgradeError as exc:
            raise KubexClientException(f"WebSocket handshake failed: {exc}") from exc
        except httpx.TimeoutException as exc:
            # Normalize to KubexClientException for symmetry with the aiohttp
            # backend, so callers using ``request_timeout`` see consistent
            # error types regardless of the underlying HTTP client.
            raise KubexClientException("WebSocket handshake timed out") from exc
        except httpx.HTTPError as exc:
            # Catches transport-level failures (``ConnectError``, ``NetworkError``,
            # TLS / DNS / proxy errors, etc.) so callers see a uniform exec
            # exception type regardless of whether the upgrade failed during
            # connect, handshake, or read. Ordered after ``TimeoutException``
            # because that is also an ``HTTPError`` subclass.
            raise KubexClientException(f"WebSocket connection failed: {exc}") from exc

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
