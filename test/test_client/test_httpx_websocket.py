from __future__ import annotations

import asyncio
import threading
from typing import Any, Generator

import pytest
from aiohttp import web

from kubex.client.httpx import HttpxClient
from kubex.client.websocket import WebSocketConnection
from kubex.configuration.configuration import ClientConfiguration
from kubex.core.exceptions import KubexClientException
from kubex.core.params import Timeout
from kubex.core.request import Request

from ._servers import ThreadedAioServer


@pytest.fixture(params=["asyncio", "trio"])
def anyio_backend(request: pytest.FixtureRequest) -> str:
    return str(request.param)


def _make_echo_app(server_protocols: list[str]) -> web.Application:
    async def echo_ws(request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse(protocols=server_protocols)
        await ws.prepare(request)
        async for msg in ws:
            if msg.type == web.WSMsgType.BINARY:
                await ws.send_bytes(msg.data)
            elif msg.type == web.WSMsgType.TEXT:
                await ws.send_str(msg.data)
            elif msg.type == web.WSMsgType.CLOSE:
                break
        return ws

    app = web.Application()
    app.router.add_get("/ws", echo_ws)
    return app


@pytest.fixture
def ws_server() -> Generator[ThreadedAioServer, None, None]:
    with ThreadedAioServer(_make_echo_app(["v5.channel.k8s.io"])) as server:
        yield server


@pytest.fixture
def ws_server_no_proto() -> Generator[ThreadedAioServer, None, None]:
    with ThreadedAioServer(_make_echo_app([])) as server:
        yield server


def _client_config(server: ThreadedAioServer) -> ClientConfiguration:
    return ClientConfiguration(url=f"http://127.0.0.1:{server.port}")


@pytest.mark.anyio
async def test_connect_websocket_returns_websocket_connection(
    ws_server: ThreadedAioServer,
) -> None:
    config = _client_config(ws_server)
    async with HttpxClient(config) as client:
        request = Request(method="GET", url="/ws")
        conn = await client.connect_websocket(request, ["v5.channel.k8s.io"])
        try:
            assert isinstance(conn, WebSocketConnection)
        finally:
            await conn.close()


@pytest.mark.anyio
async def test_connect_websocket_negotiates_subprotocol(
    ws_server: ThreadedAioServer,
) -> None:
    config = _client_config(ws_server)
    async with HttpxClient(config) as client:
        request = Request(method="GET", url="/ws")
        async with await client.connect_websocket(
            request, ["v5.channel.k8s.io"]
        ) as conn:
            assert conn.negotiated_subprotocol == "v5.channel.k8s.io"


@pytest.mark.anyio
async def test_connect_websocket_send_and_receive_bytes(
    ws_server: ThreadedAioServer,
) -> None:
    config = _client_config(ws_server)
    async with HttpxClient(config) as client:
        request = Request(method="GET", url="/ws")
        async with await client.connect_websocket(
            request, ["v5.channel.k8s.io"]
        ) as conn:
            await conn.send_bytes(b"\x01hello")
            received = await conn.receive_bytes()
            assert received == b"\x01hello"

            await conn.send_bytes(b"\x02world")
            received = await conn.receive_bytes()
            assert received == b"\x02world"


@pytest.mark.anyio
async def test_connect_websocket_close_marks_closed(
    ws_server: ThreadedAioServer,
) -> None:
    config = _client_config(ws_server)
    async with HttpxClient(config) as client:
        request = Request(method="GET", url="/ws")
        conn = await client.connect_websocket(request, ["v5.channel.k8s.io"])
        assert conn.closed is False
        await conn.close()
        assert conn.closed is True


@pytest.mark.anyio
async def test_connect_websocket_receive_after_remote_close_raises_stop(
    ws_server: ThreadedAioServer,
) -> None:
    config = _client_config(ws_server)
    async with HttpxClient(config) as client:
        request = Request(method="GET", url="/ws")
        conn = await client.connect_websocket(request, ["v5.channel.k8s.io"])
        try:
            await conn.close()
            with pytest.raises(StopAsyncIteration):
                await conn.receive_bytes()
        finally:
            if not conn.closed:
                await conn.close()


@pytest.mark.anyio
async def test_connect_websocket_subprotocol_mismatch_raises(
    ws_server_no_proto: ThreadedAioServer,
) -> None:
    config = _client_config(ws_server_no_proto)
    async with HttpxClient(config) as client:
        request = Request(method="GET", url="/ws")
        with pytest.raises(KubexClientException):
            await client.connect_websocket(request, ["v5.channel.k8s.io"])


@pytest.mark.anyio
async def test_connect_websocket_uses_request_query_params() -> None:
    captured: dict[str, list[tuple[str, str]]] = {}

    async def capture_ws(request: web.Request) -> web.WebSocketResponse:
        captured["query"] = list(request.query.items())
        ws = web.WebSocketResponse(protocols=["v5.channel.k8s.io"])
        await ws.prepare(request)
        await ws.close()
        return ws

    app = web.Application()
    app.router.add_get("/exec", capture_ws)
    with ThreadedAioServer(app) as server:
        config = ClientConfiguration(url=f"http://127.0.0.1:{server.port}")
        async with HttpxClient(config) as client:
            request = Request(
                method="GET",
                url="/exec",
                query_params={"command": "echo", "container": "main"},
            )
            conn = await client.connect_websocket(request, ["v5.channel.k8s.io"])
            await conn.close()

    assert ("command", "echo") in captured["query"]
    assert ("container", "main") in captured["query"]


@pytest.mark.anyio
async def test_connect_websocket_sends_authorization_header_when_configured() -> None:
    captured: dict[str, str | None] = {}

    async def capture_ws(request: web.Request) -> web.WebSocketResponse:
        captured["auth"] = request.headers.get("Authorization")
        ws = web.WebSocketResponse(protocols=["v5.channel.k8s.io"])
        await ws.prepare(request)
        await ws.close()
        return ws

    app = web.Application()
    app.router.add_get("/ws", capture_ws)
    with ThreadedAioServer(app) as server:
        config = ClientConfiguration(
            url=f"http://127.0.0.1:{server.port}",
            token="secret-token",
        )
        async with HttpxClient(config) as client:
            request = Request(method="GET", url="/ws")
            conn = await client.connect_websocket(request, ["v5.channel.k8s.io"])
            await conn.close()

    assert captured["auth"] == "Bearer secret-token"


def _make_abnormal_close_app(code: int) -> web.Application:
    async def closer(request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse(protocols=["v5.channel.k8s.io"])
        await ws.prepare(request)
        await ws.close(code=code, message=b"abnormal")
        return ws

    app = web.Application()
    app.router.add_get("/ws", closer)
    return app


@pytest.mark.anyio
async def test_receive_bytes_raises_on_abnormal_close_code() -> None:
    with ThreadedAioServer(_make_abnormal_close_app(1011)) as server:
        config = ClientConfiguration(url=f"http://127.0.0.1:{server.port}")
        async with HttpxClient(config) as client:
            request = Request(method="GET", url="/ws")
            conn = await client.connect_websocket(request, ["v5.channel.k8s.io"])
            try:
                with pytest.raises(KubexClientException, match="closed abnormally"):
                    await conn.receive_bytes()
            finally:
                await conn.close()


@pytest.mark.anyio
async def test_receive_bytes_treats_normal_close_as_eof() -> None:
    with ThreadedAioServer(_make_abnormal_close_app(1000)) as server:
        config = ClientConfiguration(url=f"http://127.0.0.1:{server.port}")
        async with HttpxClient(config) as client:
            request = Request(method="GET", url="/ws")
            conn = await client.connect_websocket(request, ["v5.channel.k8s.io"])
            try:
                with pytest.raises(StopAsyncIteration):
                    await conn.receive_bytes()
            finally:
                await conn.close()


class _RawCloseNoCodeServer:
    """Minimal raw-socket WebSocket server that sends a close frame with no payload.

    aiohttp's high-level ``ws.close()`` always emits a close frame carrying a
    status code (defaulting to 1000), so it cannot exercise the code-less
    close path. wsproto/httpx-ws surface a peer close frame that omits the
    status code as ``WebSocketDisconnect(code=1005)`` (NO_STATUS_RCVD) — this
    server reproduces that wire-level scenario.
    """

    def __init__(self) -> None:
        self._sock: Any = None
        self._thread: threading.Thread | None = None
        self.port: int = 0

    def start(self) -> None:
        import socket

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        self._sock = sock
        self.port = sock.getsockname()[1]

        def _serve() -> None:
            import base64
            import hashlib

            try:
                conn, _ = sock.accept()
            except OSError:
                return
            try:
                request = b""
                while b"\r\n\r\n" not in request:
                    chunk = conn.recv(4096)
                    if not chunk:
                        return
                    request += chunk
                key = b""
                for line in request.split(b"\r\n"):
                    if line.lower().startswith(b"sec-websocket-key:"):
                        key = line.split(b":", 1)[1].strip()
                        break
                accept = base64.b64encode(
                    hashlib.sha1(key + b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11").digest()
                )
                handshake = (
                    b"HTTP/1.1 101 Switching Protocols\r\n"
                    b"Upgrade: websocket\r\n"
                    b"Connection: Upgrade\r\n"
                    b"Sec-WebSocket-Accept: " + accept + b"\r\n"
                    b"Sec-WebSocket-Protocol: v5.channel.k8s.io\r\n"
                    b"\r\n"
                )
                conn.sendall(handshake)
                # CLOSE frame with empty payload — FIN=1, opcode=8, mask=0, len=0.
                conn.sendall(bytes([0x88, 0x00]))
                # Give the client time to read the frame before tearing down.
                conn.recv(4096)
            finally:
                conn.close()

        self._thread = threading.Thread(target=_serve, daemon=True, name="raw-ws")
        self._thread.start()

    def stop(self) -> None:
        if self._sock is not None:
            self._sock.close()
        if self._thread is not None:
            self._thread.join(timeout=5)


@pytest.mark.anyio
async def test_receive_bytes_treats_no_status_code_close_as_eof() -> None:
    """A peer close frame with no status code surfaces as 1005 (NO_STATUS_RCVD)
    in wsproto/httpx-ws and must be treated as a clean EOF, not an abnormal
    termination — otherwise a successful exec session could be reported as a
    failure on the httpx backend.
    """
    server = _RawCloseNoCodeServer()
    server.start()
    try:
        config = ClientConfiguration(url=f"http://127.0.0.1:{server.port}")
        async with HttpxClient(config) as client:
            request = Request(method="GET", url="/")
            conn = await client.connect_websocket(request, ["v5.channel.k8s.io"])
            try:
                with pytest.raises(StopAsyncIteration):
                    await conn.receive_bytes()
            finally:
                await conn.close()
    finally:
        server.stop()


@pytest.mark.anyio
async def test_connect_websocket_forwards_request_timeout_to_handshake() -> None:
    """A small handshake timeout against an unresponsive endpoint should
    fast-fail rather than hanging on the client default.

    The handshake timeout must surface as ``KubexClientException`` for
    symmetry with the aiohttp backend, not as a backend-native
    ``httpx.TimeoutException``.
    """

    async def hang_forever(request: web.Request) -> web.WebSocketResponse:
        await asyncio.sleep(2.0)
        ws = web.WebSocketResponse(protocols=["v5.channel.k8s.io"])
        await ws.prepare(request)
        return ws

    app = web.Application()
    app.router.add_get("/ws", hang_forever)
    with ThreadedAioServer(app) as server:
        config = ClientConfiguration(url=f"http://127.0.0.1:{server.port}")
        async with HttpxClient(config) as client:
            request = Request(method="GET", url="/ws", timeout=Timeout(total=0.1))
            with pytest.raises(KubexClientException, match="handshake timed out"):
                await client.connect_websocket(request, ["v5.channel.k8s.io"])


@pytest.mark.anyio
async def test_connect_websocket_wraps_transport_error_as_kubex_exception() -> None:
    """A connection refused / DNS failure during the upgrade must surface as
    ``KubexClientException``, not a raw ``httpx.ConnectError``.

    The exec layer documents a backend-agnostic exception contract; if
    transport-level failures during the WebSocket upgrade leaked the native
    httpx type, callers using ``except KubexClientException`` would have to
    special-case the underlying client.
    """
    # 127.0.0.1:1 is reserved (tcpmux) and reliably refuses connections.
    config = ClientConfiguration(url="http://127.0.0.1:1")
    async with HttpxClient(config) as client:
        request = Request(method="GET", url="/ws")
        with pytest.raises(KubexClientException, match="connection failed"):
            await client.connect_websocket(request, ["v5.channel.k8s.io"])


@pytest.mark.anyio
async def test_send_bytes_wraps_websocket_disconnect_as_kubex_exception() -> None:
    """A peer disconnect during ``send_bytes`` must surface as
    ``KubexClientException``, not a raw ``httpx_ws.WebSocketDisconnect``."""
    from contextlib import AbstractAsyncContextManager

    from httpx_ws import WebSocketDisconnect

    from kubex.client.httpx import HttpxWebSocketConnection

    class _FakeSession:
        subprotocol: str | None = "v5.channel.k8s.io"

        async def send_bytes(self, data: bytes) -> None:
            raise WebSocketDisconnect(code=1006, reason=None)

        async def receive_bytes(self) -> bytes:
            return b""

    class _FakeCM(AbstractAsyncContextManager[Any]):
        async def __aenter__(self) -> Any:
            return None

        async def __aexit__(self, *exc_info: Any) -> None:
            return None

    cm = _FakeCM()
    conn = HttpxWebSocketConnection(cm, _FakeSession())  # type: ignore[arg-type]
    try:
        with pytest.raises(KubexClientException, match="send failed"):
            await conn.send_bytes(b"\x00data")
    finally:
        await conn.close()


@pytest.mark.anyio
async def test_send_bytes_wraps_closed_resource_error_as_kubex_exception() -> None:
    """``ClosedResourceError`` during ``send_bytes`` must surface as
    ``KubexClientException``."""
    from contextlib import AbstractAsyncContextManager

    from anyio import ClosedResourceError

    from kubex.client.httpx import HttpxWebSocketConnection

    class _FakeSession:
        subprotocol: str | None = "v5.channel.k8s.io"

        async def send_bytes(self, data: bytes) -> None:
            raise ClosedResourceError

        async def receive_bytes(self) -> bytes:
            return b""

    class _FakeCM(AbstractAsyncContextManager[Any]):
        async def __aenter__(self) -> Any:
            return None

        async def __aexit__(self, *exc_info: Any) -> None:
            return None

    cm = _FakeCM()
    conn = HttpxWebSocketConnection(cm, _FakeSession())  # type: ignore[arg-type]
    try:
        with pytest.raises(KubexClientException, match="connection closed"):
            await conn.send_bytes(b"\x00data")
    finally:
        await conn.close()


@pytest.mark.anyio
async def test_close_after_peer_disconnect_releases_underlying_cm() -> None:
    """``close()`` must always release the underlying httpx-ws context manager.

    An earlier implementation marked the adapter as closed on the first
    ``WebSocketDisconnect``/``WebSocketNetworkError``/``ClosedResourceError``
    seen in ``receive_bytes``. The subsequent ``close()`` then short-circuited
    on that flag and never invoked ``cm.__aexit__()``, leaking the underlying
    HTTP connection. The flags must be split so EOF observation does not
    suppress the cleanup path.
    """
    from contextlib import AbstractAsyncContextManager

    from kubex.client.httpx import HttpxWebSocketConnection

    class _FakeSession:
        subprotocol: str | None = "v5.channel.k8s.io"

        async def receive_bytes(self) -> bytes:
            from httpx_ws import WebSocketDisconnect

            raise WebSocketDisconnect(code=1000, reason=None)

        async def send_bytes(self, data: bytes) -> None:
            return None

    class _FakeCM(AbstractAsyncContextManager[Any]):
        def __init__(self) -> None:
            self.exit_calls = 0

        async def __aenter__(self) -> Any:
            return None

        async def __aexit__(self, *exc_info: Any) -> None:
            self.exit_calls += 1

    cm = _FakeCM()
    conn = HttpxWebSocketConnection(cm, _FakeSession())  # type: ignore[arg-type]

    with pytest.raises(StopAsyncIteration):
        await conn.receive_bytes()
    assert cm.exit_calls == 0, "EOF must not preempt cleanup of the cm"

    await conn.close()
    assert cm.exit_calls == 1, "close() must release the underlying cm exactly once"

    # Idempotent: a second close() must not double-exit the cm.
    await conn.close()
    assert cm.exit_calls == 1


@pytest.mark.anyio
async def test_receive_bytes_rejects_text_frame_as_kubex_exception() -> None:
    """A text frame on the v5 channel protocol is a server-side protocol
    violation. ``httpx_ws.AsyncWebSocketSession.receive_bytes()`` raises
    ``WebSocketInvalidTypeReceived`` in this case; the adapter must
    normalize that to ``KubexClientException`` rather than leaking the
    backend-specific exception type to callers.
    """
    from contextlib import AbstractAsyncContextManager

    import wsproto.events
    from httpx_ws import WebSocketInvalidTypeReceived

    from kubex.client.httpx import HttpxWebSocketConnection

    class _FakeSession:
        subprotocol: str | None = "v5.channel.k8s.io"

        async def send_bytes(self, data: bytes) -> None:
            return None

        async def receive_bytes(self) -> bytes:
            raise WebSocketInvalidTypeReceived(wsproto.events.TextMessage(data="oops"))

    class _FakeCM(AbstractAsyncContextManager[Any]):
        async def __aenter__(self) -> Any:
            return None

        async def __aexit__(self, *exc_info: Any) -> None:
            return None

    cm = _FakeCM()
    conn = HttpxWebSocketConnection(cm, _FakeSession())  # type: ignore[arg-type]
    try:
        with pytest.raises(KubexClientException, match="non-binary frame"):
            await conn.receive_bytes()
    finally:
        await conn.close()
