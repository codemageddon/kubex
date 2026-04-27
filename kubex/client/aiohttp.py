import ssl
import warnings
from typing import Any, AsyncGenerator, Sequence

import anyio
from aiohttp import (
    ClientError,
    ClientSession,
    ClientTimeout,
    ClientWebSocketResponse,
    WSMsgType,
    WSServerHandshakeError,
)
from aiohttp.connector import TCPConnector

from kubex.client.websocket import WebSocketConnection
from kubex.configuration import ClientConfiguration
from kubex.core.exceptions import KubexClientException
from kubex.core.params import Timeout
from kubex.core.request import Request
from kubex.core.request_builder import constants
from kubex.core.response import HeadersWrapper, Response

from .client import (
    BaseClient,
    handle_request_error,
)


def _to_aiohttp_timeout(timeout: Timeout | None) -> ClientTimeout:
    """Translate a ``Timeout`` (or explicit ``None``) to ``ClientTimeout``.

    ``write`` and ``pool`` are ignored: aiohttp does not support them.
    """
    if timeout is None:
        return ClientTimeout(total=None)
    return ClientTimeout(
        total=timeout.total,
        sock_connect=timeout.connect,
        sock_read=timeout.read,
    )


class AioHttpClient(BaseClient):
    def __init__(self, configuration: ClientConfiguration) -> None:
        self._configuration = configuration
        self._default_headers = {
            constants.CONTENT_TYPE_HEADER: constants.APPLICATION_JSON_MIME_TYPE,
            constants.ACCEPT_HEADER: constants.APPLICATION_JSON_MIME_TYPE,
        }
        self._inner_client: ClientSession = self._create_inner_client()

    @property
    def configuration(self) -> ClientConfiguration:
        return self._configuration

    def _get_headers(self) -> dict[str, str]:
        if self.configuration.token is None:
            return {}
        return {"Authorization": f"Bearer {self.configuration.token}"}

    def _create_inner_client(self) -> ClientSession:
        ssl_context = ssl.create_default_context(
            cafile=self.configuration.server_ca_file
        )
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

        connector = TCPConnector(
            verify_ssl=not bool(self.configuration.insecure_skip_tls_verify),
            ssl=ssl_context,
        )
        kwargs: dict[str, Any] = {
            "base_url": str(self.configuration.base_url),
            "connector": connector,
            "read_bufsize": 2**21,
            "headers": self._default_headers,
        }
        configured_timeout = self.configuration.timeout
        if configured_timeout is not Ellipsis:
            kwargs["timeout"] = _to_aiohttp_timeout(configured_timeout)
        return ClientSession(**kwargs)

    async def request(self, request: Request) -> Response:
        headers = self._get_headers()
        if request.headers:
            headers.update(request.headers)
        extra: dict[str, Any] = {}
        if request.timeout is not Ellipsis:
            extra["timeout"] = _to_aiohttp_timeout(request.timeout)
        _response = await self._inner_client.request(
            method=request.method,
            url=request.url,
            params=request.query_params,
            data=request.body,
            headers=headers,
            **extra,
        )
        status = _response.status
        response = Response(
            status_code=status,
            headers=HeadersWrapper(_response.headers),
            content=await _response.read(),
        )
        if self.configuration.log_api_warnings and (
            api_warnings := _response.headers.get("Warning")
        ):
            for warning in api_warnings.split(","):
                warnings.warn(f"API Warning: {warning}")
        if 400 <= status < 600:
            handle_request_error(response)
        return response

    async def stream_lines(self, request: Request) -> AsyncGenerator[str, None]:
        headers = self._get_headers()
        if request.headers:
            headers.update(request.headers)
        extra: dict[str, Any] = {}
        if request.timeout is not Ellipsis:
            extra["timeout"] = _to_aiohttp_timeout(request.timeout)
        _response = await self._inner_client.request(
            method=request.method,
            url=request.url,
            params=request.query_params,
            data=request.body,
            headers=headers,
            **extra,
        )
        try:
            status = _response.status
            if 400 <= status < 600:
                response = Response(
                    status_code=status,
                    headers=HeadersWrapper(_response.headers),
                    content=await _response.read(),
                )
                handle_request_error(response)
            while line := await _response.content.readline():
                yield line.decode("utf-8")
        finally:
            _response.close()

    async def close(self) -> None:
        await self._inner_client.close()

    async def connect_websocket(
        self,
        request: Request,
        subprotocols: Sequence[str],
    ) -> WebSocketConnection:
        headers = self._get_headers()
        if request.headers:
            headers.update(request.headers)

        params: Any = (
            request.query_param_pairs
            if request.query_param_pairs is not None
            else request.query_params
        )

        # aiohttp's ``ws_connect`` does not accept an HTTP-level timeout
        # override (its ``timeout=`` is ``ClientWSTimeout`` controlling
        # ``ws_close``/``ws_receive``). The HTTP upgrade is bounded by the
        # session's ``ClientTimeout``, which is fixed at session construction.
        # To honor the public ``request_timeout`` contract on a per-call basis
        # — ``None`` disables timeouts entirely; an explicit ``Timeout``
        # overrides the configured default — perform the upgrade through a
        # temporary ``ClientSession`` that shares the persistent connector via
        # ``connector_owner=False``. The temporary session is closed
        # immediately after the upgrade; the WebSocket continues to function
        # because it holds its connection from the shared connector rather
        # than from the session itself.
        #
        # Additionally bound the upgrade with an outer cancel scope when
        # ``total`` is set, as defense-in-depth in case aiohttp's session
        # timeout misfires. The outer guard is driven by ``total`` only:
        # ``Timeout.connect`` is documented to bound only TCP connection
        # establishment, and ``Timeout.read`` only inter-chunk reads — those
        # per-phase semantics are honored via the temporary session's
        # ``sock_connect``/``sock_read`` (set by ``_to_aiohttp_timeout``).
        handshake_timeout: float | None = None
        if request.timeout is not Ellipsis and request.timeout is not None:
            handshake_timeout = request.timeout.total

        upgrade_session: ClientSession
        temp_session: ClientSession | None = None
        if request.timeout is Ellipsis:
            upgrade_session = self._inner_client
        else:
            temp_session = ClientSession(
                base_url=str(self._configuration.base_url),
                connector=self._inner_client.connector,
                connector_owner=False,
                headers=self._default_headers,
                timeout=_to_aiohttp_timeout(request.timeout),
            )
            upgrade_session = temp_session

        # aiohttp defaults ``max_msg_size`` to 4 MiB on ``ws_connect`` while
        # the httpx-ws adapter caps frames at 2 MiB; explicitly match here so
        # large exec stdout/stderr chunks fail (or succeed) the same way on
        # both backends.
        try:
            if handshake_timeout is not None:
                with anyio.fail_after(handshake_timeout):
                    ws = await upgrade_session.ws_connect(
                        request.url,
                        protocols=tuple(subprotocols),
                        headers=headers,
                        params=params,
                        max_msg_size=2**21,
                    )
            else:
                ws = await upgrade_session.ws_connect(
                    request.url,
                    protocols=tuple(subprotocols),
                    headers=headers,
                    params=params,
                    max_msg_size=2**21,
                )
        except WSServerHandshakeError as exc:
            raise KubexClientException(f"WebSocket handshake failed: {exc}") from exc
        except TimeoutError as exc:
            # ``TimeoutError`` may originate from our outer cancel scope OR
            # from aiohttp's per-call ``ClientTimeout`` (e.g. ``sock_connect``/
            # ``sock_read`` via ``ConnectionTimeoutError``/``SocketTimeoutError``,
            # both ``TimeoutError`` subclasses). The actual fired bound is not
            # always our ``handshake_timeout`` — keep the message general.
            raise KubexClientException("WebSocket handshake timed out") from exc
        except ClientError as exc:
            # Covers transport-level failures during the upgrade
            # (``ClientConnectorError``, ``ServerDisconnectedError``,
            # TLS / DNS / proxy errors, etc.) so callers see a uniform exec
            # exception type regardless of whether the upgrade failed during
            # connect, handshake, or read. Ordered after
            # ``WSServerHandshakeError`` because that is also a ``ClientError``
            # subclass and carries a more specific message.
            raise KubexClientException(f"WebSocket connection failed: {exc}") from exc
        finally:
            if temp_session is not None:
                await temp_session.close()

        if subprotocols and ws.protocol is None:
            # Suppress any cleanup error so the descriptive subprotocol
            # mismatch is what the caller sees, rather than a transport
            # close failure masking the real diagnosis. ``except Exception``
            # (not ``BaseException``) so a ``Cancelled`` raised during the
            # close propagates and cooperative cancellation is not dropped.
            try:
                await ws.close()
            except Exception:
                pass
            raise KubexClientException(
                "Server did not negotiate any of the requested subprotocols: "
                f"{list(subprotocols)}"
            )

        return AioHttpWebSocketConnection(ws)


class AioHttpWebSocketConnection(WebSocketConnection):
    """Adapter wrapping an :class:`aiohttp.ClientWebSocketResponse`."""

    def __init__(self, ws: ClientWebSocketResponse) -> None:
        self._ws = ws
        self._client_closed = False
        self._peer_closed_clean = False

    @property
    def closed(self) -> bool:
        return self._ws.closed

    @property
    def negotiated_subprotocol(self) -> str | None:
        return self._ws.protocol

    async def send_bytes(self, data: bytes) -> None:
        try:
            await self._ws.send_bytes(data)
        except ConnectionResetError as exc:
            # aiohttp raises bare ``ConnectionResetError`` when the underlying
            # transport has gone away. Normalize for symmetry with the receive
            # path so callers writing stdin or resize frames see
            # ``KubexClientException`` rather than the raw OS-level exception.
            raise KubexClientException(
                "WebSocket send failed: connection reset"
            ) from exc
        except ClientError as exc:
            raise KubexClientException(f"WebSocket send failed: {exc}") from exc

    async def receive_bytes(self) -> bytes:
        if self._client_closed or self._peer_closed_clean:
            raise StopAsyncIteration
        msg = await self._ws.receive()
        # A concurrent ``close()`` unblocks an in-flight ``receive()`` by
        # feeding ``WS_CLOSING_MESSAGE`` (``WSMsgType.CLOSING``). When the
        # local side initiated the shutdown this is normal teardown, not a
        # transport-loss event — short-circuit before classifying the
        # message type.
        if self._client_closed:
            raise StopAsyncIteration
        match msg.type:
            case WSMsgType.BINARY:
                data: bytes = msg.data
                return data
            case WSMsgType.TEXT:
                # The K8s exec/attach/port-forward subresources only ever send
                # binary frames over v5.channel.k8s.io. A text frame is a
                # protocol violation; raise a normalized client exception
                # rather than UTF-8 encoding it into bytes that the channel
                # protocol decoder would then misparse as a regular frame.
                raise KubexClientException(
                    "WebSocket received unexpected non-binary frame"
                )
            case WSMsgType.CLOSE:
                # msg.data carries the peer's close code (int). 1000
                # (NORMAL_CLOSURE), 1001 (GOING_AWAY) and 1005 (NO_STATUS_RCVD,
                # i.e. close with no code) are treated as clean EOF; any other
                # code indicates an abnormal termination that the caller should
                # see rather than confuse with a clean exec completion.
                # aiohttp's reader emits ``msg.data = 0`` for an empty-payload
                # close frame (RFC 6455 ``0x88 0x00``) — wsproto/httpx-ws
                # surface the same wire-level scenario as ``code=1005``, so we
                # treat ``0`` as a clean EOF for backend symmetry.
                close_code = msg.data if isinstance(msg.data, int) else None
                if close_code is None or close_code in (0, 1000, 1001, 1005):
                    self._peer_closed_clean = True
                    raise StopAsyncIteration
                raise KubexClientException(
                    f"WebSocket closed abnormally "
                    f"(code={close_code}, reason={msg.extra!r})"
                )
            case WSMsgType.CLOSED | WSMsgType.CLOSING:
                # Reaching this branch without a prior clean ``WSMsgType.CLOSE``
                # means the transport ended without a close frame: aiohttp
                # converts both ``ClientError`` (transport loss) and
                # ``EofStream`` (transport EOF) into ``WSMsgType.CLOSED``, with
                # ``ws.close_code`` set to ``1006`` in the former case and
                # ``1000`` in the latter.
                # Furthermore, on Python 3.10 + TLS, abrupt websocket drops
                # are reported via ``EofStream`` (close_code=1000) rather than
                # ``ClientError`` (aio-libs/aiohttp#8138), so the close code
                # alone cannot distinguish a clean disconnect from transport
                # loss. K8s exec always sends a close frame on success, so
                # treat the whole transport-EOF class as abnormal: this
                # ensures a broken exec stream is never mistaken for a
                # successful completion.
                # (A prior clean ``WSMsgType.CLOSE`` is handled above via the
                # ``_peer_closed_clean`` short-circuit, since aiohttp's
                # ``receive()`` autocloses the websocket and reports CLOSED
                # on every subsequent call.)
                close_code = self._ws.close_code
                raise KubexClientException(
                    f"WebSocket closed abnormally (code={close_code})"
                )
            case WSMsgType.ERROR:
                exc = self._ws.exception()
                if exc is not None:
                    raise KubexClientException(f"WebSocket error: {exc}") from exc
                raise KubexClientException("WebSocket error")
            case _:
                raise KubexClientException(
                    f"Unexpected WebSocket message type: {msg.type}"
                )

    async def close(self) -> None:
        self._client_closed = True
        await self._ws.close()
