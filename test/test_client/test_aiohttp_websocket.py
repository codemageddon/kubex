from __future__ import annotations

from typing import Any, AsyncGenerator

import pytest
from aiohttp import WSMsgType, web
from aiohttp.test_utils import TestServer

from kubex.client.aiohttp import AioHttpClient
from kubex.client.options import ClientOptions
from kubex.client.websocket import WebSocketConnection
from kubex.configuration.configuration import ClientConfiguration
from kubex.core.exceptions import KubexClientException
from kubex.core.params import Timeout
from kubex.core.request import Request


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


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
async def ws_server() -> AsyncGenerator[TestServer, None]:
    server = TestServer(_make_echo_app(["v5.channel.k8s.io"]))
    async with server:
        yield server


@pytest.fixture
async def ws_server_no_proto() -> AsyncGenerator[TestServer, None]:
    server = TestServer(_make_echo_app([]))
    async with server:
        yield server


def _client_config(server: TestServer) -> ClientConfiguration:
    return ClientConfiguration(url=str(server.make_url("/")))


@pytest.mark.anyio
async def test_connect_websocket_returns_websocket_connection(
    ws_server: TestServer,
) -> None:
    config = _client_config(ws_server)
    async with AioHttpClient(config) as client:
        request = Request(method="GET", url="/ws")
        conn = await client.connect_websocket(request, ["v5.channel.k8s.io"])
        try:
            assert isinstance(conn, WebSocketConnection)
        finally:
            await conn.close()


@pytest.mark.anyio
async def test_connect_websocket_negotiates_subprotocol(
    ws_server: TestServer,
) -> None:
    config = _client_config(ws_server)
    async with AioHttpClient(config) as client:
        request = Request(method="GET", url="/ws")
        async with await client.connect_websocket(
            request, ["v5.channel.k8s.io"]
        ) as conn:
            assert conn.negotiated_subprotocol == "v5.channel.k8s.io"


@pytest.mark.anyio
async def test_connect_websocket_send_and_receive_bytes(
    ws_server: TestServer,
) -> None:
    config = _client_config(ws_server)
    async with AioHttpClient(config) as client:
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
    ws_server: TestServer,
) -> None:
    config = _client_config(ws_server)
    async with AioHttpClient(config) as client:
        request = Request(method="GET", url="/ws")
        conn = await client.connect_websocket(request, ["v5.channel.k8s.io"])
        assert conn.closed is False
        await conn.close()
        assert conn.closed is True


@pytest.mark.anyio
async def test_connect_websocket_receive_after_remote_close_raises_stop(
    ws_server: TestServer,
) -> None:
    config = _client_config(ws_server)
    async with AioHttpClient(config) as client:
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
    ws_server_no_proto: TestServer,
) -> None:
    config = _client_config(ws_server_no_proto)
    async with AioHttpClient(config) as client:
        request = Request(method="GET", url="/ws")
        with pytest.raises(KubexClientException):
            await client.connect_websocket(request, ["v5.channel.k8s.io"])


@pytest.mark.anyio
async def test_connect_websocket_uses_request_query_params(
    ws_server: TestServer,
) -> None:
    captured: dict[str, list[tuple[str, str]]] = {}

    async def capture_ws(request: web.Request) -> web.WebSocketResponse:
        captured["query"] = list(request.query.items())
        ws = web.WebSocketResponse(protocols=["v5.channel.k8s.io"])
        await ws.prepare(request)
        await ws.close()
        return ws

    app = web.Application()
    app.router.add_get("/exec", capture_ws)
    server = TestServer(app)
    async with server:
        config = ClientConfiguration(url=str(server.make_url("/")))
        async with AioHttpClient(config) as client:
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
    server = TestServer(app)
    async with server:
        config = ClientConfiguration(
            url=str(server.make_url("/")),
            token="secret-token",
        )
        async with AioHttpClient(config) as client:
            request = Request(method="GET", url="/ws")
            conn = await client.connect_websocket(request, ["v5.channel.k8s.io"])
            await conn.close()

    assert captured["auth"] == "Bearer secret-token"


@pytest.mark.anyio
async def test_receive_bytes_raises_on_abnormal_close_code() -> None:
    async def server_closes_abnormally(request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse(protocols=["v5.channel.k8s.io"])
        await ws.prepare(request)
        await ws.close(code=1011, message=b"server error")
        return ws

    app = web.Application()
    app.router.add_get("/ws", server_closes_abnormally)
    server = TestServer(app)
    async with server:
        config = ClientConfiguration(url=str(server.make_url("/")))
        async with AioHttpClient(config) as client:
            request = Request(method="GET", url="/ws")
            conn = await client.connect_websocket(request, ["v5.channel.k8s.io"])
            try:
                with pytest.raises(KubexClientException, match="closed abnormally"):
                    await conn.receive_bytes()
            finally:
                await conn.close()


@pytest.mark.anyio
async def test_receive_bytes_treats_normal_close_as_eof() -> None:
    async def server_closes_normally(request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse(protocols=["v5.channel.k8s.io"])
        await ws.prepare(request)
        await ws.close(code=1000)
        return ws

    app = web.Application()
    app.router.add_get("/ws", server_closes_normally)
    server = TestServer(app)
    async with server:
        config = ClientConfiguration(url=str(server.make_url("/")))
        async with AioHttpClient(config) as client:
            request = Request(method="GET", url="/ws")
            conn = await client.connect_websocket(request, ["v5.channel.k8s.io"])
            try:
                with pytest.raises(StopAsyncIteration):
                    await conn.receive_bytes()
            finally:
                await conn.close()


@pytest.mark.anyio
async def test_receive_bytes_after_clean_close_keeps_raising_stop_async_iteration() -> (
    None
):
    """Repeated ``receive_bytes`` after a clean peer close must keep raising
    ``StopAsyncIteration`` rather than reporting an abnormal close.

    aiohttp's ``ClientWebSocketResponse.receive`` returns ``WSMsgType.CLOSE``
    once for the peer's close frame and then auto-closes the websocket; every
    subsequent ``receive`` reports ``WSMsgType.CLOSED``. The adapter must
    remember the prior clean close so it does not retroactively reclassify
    EOF as transport loss on the second call.
    """

    async def server_closes_normally(request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse(protocols=["v5.channel.k8s.io"])
        await ws.prepare(request)
        await ws.close(code=1000)
        return ws

    app = web.Application()
    app.router.add_get("/ws", server_closes_normally)
    server = TestServer(app)
    async with server:
        config = ClientConfiguration(url=str(server.make_url("/")))
        async with AioHttpClient(config) as client:
            request = Request(method="GET", url="/ws")
            conn = await client.connect_websocket(request, ["v5.channel.k8s.io"])
            try:
                with pytest.raises(StopAsyncIteration):
                    await conn.receive_bytes()
                with pytest.raises(StopAsyncIteration):
                    await conn.receive_bytes()
            finally:
                await conn.close()


@pytest.mark.anyio
async def test_connect_websocket_handshake_timeout() -> None:
    import asyncio

    async def slow_handshake(request: web.Request) -> web.WebSocketResponse:
        await asyncio.sleep(2.0)
        ws = web.WebSocketResponse(protocols=["v5.channel.k8s.io"])
        await ws.prepare(request)
        return ws

    app = web.Application()
    app.router.add_get("/ws", slow_handshake)
    server = TestServer(app)
    async with server:
        config = ClientConfiguration(url=str(server.make_url("/")))
        async with AioHttpClient(config) as client:
            request = Request(method="GET", url="/ws", timeout=Timeout(total=0.05))
            with pytest.raises(KubexClientException, match="handshake timed out"):
                await client.connect_websocket(request, ["v5.channel.k8s.io"])


@pytest.mark.anyio
async def test_connect_websocket_handshake_timeout_prefers_total_over_connect() -> None:
    """``Timeout.total`` must bound the handshake even when ``connect`` is also set.

    Regression test: an earlier implementation used ``connect or total`` which
    silently ignored ``total`` whenever ``connect`` was truthy. With
    ``total=0.1, connect=5.0`` against a slow server the handshake must fail
    fast (under ~1s) using ``total``, not wait ~5s on ``connect``.
    """
    import asyncio
    import time

    async def slow_handshake(request: web.Request) -> web.WebSocketResponse:
        await asyncio.sleep(2.0)
        ws = web.WebSocketResponse(protocols=["v5.channel.k8s.io"])
        await ws.prepare(request)
        return ws

    app = web.Application()
    app.router.add_get("/ws", slow_handshake)
    server = TestServer(app)
    async with server:
        config = ClientConfiguration(url=str(server.make_url("/")))
        async with AioHttpClient(config) as client:
            request = Request(
                method="GET",
                url="/ws",
                timeout=Timeout(total=0.1, connect=5.0),
            )
            started = time.monotonic()
            with pytest.raises(KubexClientException, match="handshake timed out"):
                await client.connect_websocket(request, ["v5.channel.k8s.io"])
            elapsed = time.monotonic() - started
            assert elapsed < 1.0, (
                f"handshake honored connect={5.0} instead of total=0.1; "
                f"elapsed {elapsed:.3f}s"
            )


@pytest.mark.anyio
async def test_connect_websocket_request_timeout_none_disables_session_timeout() -> (
    None
):
    """``request_timeout=None`` must disable the session-level timeout for that call.

    The public ``request_timeout`` contract on ``Api`` says ``None`` disables
    timeouts entirely for that call. aiohttp's ``ws_connect`` uses the
    session's ``ClientTimeout`` for the HTTP upgrade, so honoring the
    contract requires the upgrade to bypass that session-level bound. With
    a tight session timeout against a slow handshake, ``request.timeout=None``
    must let the handshake complete; the same scenario without the override
    must time out.
    """
    import asyncio

    delay = 0.5

    async def slow_handshake(request: web.Request) -> web.WebSocketResponse:
        await asyncio.sleep(delay)
        ws = web.WebSocketResponse(protocols=["v5.channel.k8s.io"])
        await ws.prepare(request)
        await ws.close()
        return ws

    app = web.Application()
    app.router.add_get("/ws", slow_handshake)
    server = TestServer(app)
    async with server:
        # Configure session timeout *shorter* than the handshake delay.
        config = ClientConfiguration(url=str(server.make_url("/")))
        opts = ClientOptions(timeout=Timeout(total=0.1))
        async with AioHttpClient(config, opts) as client:
            # Sanity check: without the per-call override, the session
            # timeout fires and the handshake fails fast.
            request_default = Request(method="GET", url="/ws")
            with pytest.raises(KubexClientException, match="handshake timed out"):
                await client.connect_websocket(request_default, ["v5.channel.k8s.io"])

            # With ``request.timeout=None`` the per-call override disables
            # the session timeout for this call, so the handshake completes.
            request_no_timeout = Request(method="GET", url="/ws", timeout=None)
            conn = await client.connect_websocket(
                request_no_timeout, ["v5.channel.k8s.io"]
            )
            try:
                assert conn.negotiated_subprotocol == "v5.channel.k8s.io"
            finally:
                await conn.close()


@pytest.mark.anyio
async def test_receive_bytes_surfaces_transport_loss_as_abnormal() -> None:
    """A broken transport (server abruptly drops the connection) must surface
    as ``KubexClientException`` rather than a clean ``StopAsyncIteration``.

    aiohttp's ``ClientWebSocketResponse.receive`` translates ``ClientError``
    (e.g. ``ServerDisconnectedError``) into ``WSMsgType.CLOSED`` with
    ``close_code = 1006`` (``ABNORMAL_CLOSURE``). Without inspecting the close
    code, transport loss would be indistinguishable from clean EOF and an
    ``StreamSession`` would treat a broken stream as a successful exit.
    """

    async def drop_connection(request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse(protocols=["v5.channel.k8s.io"])
        await ws.prepare(request)
        # Force the underlying transport closed without sending a close frame
        # — this is what surfaces inside aiohttp as a ClientError on read.
        transport = request.transport
        assert transport is not None
        transport.close()
        return ws

    app = web.Application()
    app.router.add_get("/ws", drop_connection)
    server = TestServer(app)
    async with server:
        config = ClientConfiguration(url=str(server.make_url("/")))
        async with AioHttpClient(config) as client:
            request = Request(method="GET", url="/ws")
            conn = await client.connect_websocket(request, ["v5.channel.k8s.io"])
            try:
                with pytest.raises(KubexClientException, match="closed abnormally"):
                    await conn.receive_bytes()
            finally:
                await conn.close()


@pytest.mark.anyio
async def test_receive_bytes_surfaces_eofstream_close_as_abnormal() -> None:
    """``WSMsgType.CLOSED`` with ``close_code=1000`` must still be reported as
    abnormal, not a clean EOF.

    aiohttp converts an ``EofStream`` (transport EOF without a WebSocket close
    frame) into ``WSMsgType.CLOSED`` with ``close_code = 1000`` (OK). On
    Python 3.10 + TLS, an *abrupt* websocket drop is also reported via this
    ``EofStream`` pathway rather than as ``ClientError``
    (aio-libs/aiohttp#8138), so trusting ``close_code == 1000`` here would
    misclassify transport loss as a successful exec exit. K8s exec always
    sends a close frame on success, so any CLOSED/CLOSING surfaces a broken
    stream and must raise ``KubexClientException``.

    This test mocks ``ClientWebSocketResponse`` rather than driving a live
    server because reproducing the Python 3.10 + TLS aiohttp bug requires a
    very specific runtime/transport combination; the mock pins the contract
    that the kubex adapter does not rely on close codes here.
    """
    from kubex.client.aiohttp import AioHttpWebSocketConnection

    class _FakeMessage:
        def __init__(self) -> None:
            self.type = WSMsgType.CLOSED
            self.data: int | None = None
            self.extra: str | None = None

    class _FakeWs:
        def __init__(self) -> None:
            self.closed = False
            self.protocol: str | None = "v5.channel.k8s.io"
            self.close_code: int | None = 1000  # EofStream → OK

        async def receive(self) -> _FakeMessage:
            return _FakeMessage()

        async def close(self) -> None:
            self.closed = True

    fake_ws: Any = _FakeWs()
    conn = AioHttpWebSocketConnection(fake_ws)
    try:
        with pytest.raises(KubexClientException, match="closed abnormally"):
            await conn.receive_bytes()
    finally:
        await conn.close()


@pytest.mark.anyio
async def test_receive_bytes_treats_no_status_code_close_as_eof() -> None:
    """A peer close frame with an empty payload (RFC 6455 ``0x88 0x00``) must
    be treated as a clean EOF, mirroring the httpx adapter.

    aiohttp's reader emits ``WSMessage(WSMsgType.CLOSE, 0, "")`` for empty
    close frames. wsproto/httpx-ws surface the same wire-level scenario as
    ``WebSocketDisconnect(code=1005)`` (NO_STATUS_RCVD) — without
    normalising ``code=0`` here, a successful exec session against a server
    that omits the close-code would fail on aiohttp while succeeding on
    httpx.

    This test mocks ``ClientWebSocketResponse`` rather than driving a live
    server because aiohttp's high-level ``ws.close()`` always sends a code,
    so it cannot exercise the code-less close path.
    """
    from kubex.client.aiohttp import AioHttpWebSocketConnection

    class _FakeMessage:
        def __init__(self) -> None:
            self.type = WSMsgType.CLOSE
            self.data: int = 0  # empty close frame
            self.extra: str = ""

    class _FakeWs:
        def __init__(self) -> None:
            self.closed = False
            self.protocol: str | None = "v5.channel.k8s.io"
            self.close_code: int | None = 1005

        async def receive(self) -> _FakeMessage:
            return _FakeMessage()

        async def close(self) -> None:
            self.closed = True

    fake_ws: Any = _FakeWs()
    conn = AioHttpWebSocketConnection(fake_ws)
    try:
        with pytest.raises(StopAsyncIteration):
            await conn.receive_bytes()
    finally:
        await conn.close()


@pytest.mark.anyio
async def test_connect_websocket_wraps_transport_error_as_kubex_exception() -> None:
    """A connection refused / DNS failure during the upgrade must surface as
    ``KubexClientException``, not a raw ``aiohttp.ClientConnectorError``.

    The exec layer documents a backend-agnostic exception contract; if
    transport-level failures during the WebSocket upgrade leaked the native
    aiohttp type, callers using ``except KubexClientException`` would have
    to special-case the underlying client.
    """
    # 127.0.0.1:1 is reserved (tcpmux) and reliably refuses connections.
    config = ClientConfiguration(url="http://127.0.0.1:1")
    async with AioHttpClient(config) as client:
        request = Request(method="GET", url="/ws")
        with pytest.raises(KubexClientException, match="connection failed"):
            await client.connect_websocket(request, ["v5.channel.k8s.io"])


@pytest.mark.anyio
async def test_send_bytes_wraps_connection_reset_as_kubex_exception() -> None:
    """A broken transport during ``send_bytes`` must surface as
    ``KubexClientException``, not a raw ``ConnectionResetError``."""
    from kubex.client.aiohttp import AioHttpWebSocketConnection

    class _FakeWs:
        def __init__(self) -> None:
            self.closed = False
            self.protocol: str | None = "v5.channel.k8s.io"
            self.close_code: int | None = None

        async def send_bytes(self, data: bytes) -> None:
            raise ConnectionResetError("Cannot write to closing transport")

        async def close(self) -> None:
            self.closed = True

    fake_ws: Any = _FakeWs()
    conn = AioHttpWebSocketConnection(fake_ws)
    try:
        with pytest.raises(KubexClientException, match="connection reset"):
            await conn.send_bytes(b"\x00data")
    finally:
        await conn.close()


@pytest.mark.anyio
async def test_send_bytes_wraps_client_error_as_kubex_exception() -> None:
    """Generic ``ClientError`` during send must surface as
    ``KubexClientException``."""
    from aiohttp import ClientError

    from kubex.client.aiohttp import AioHttpWebSocketConnection

    class _FakeWs:
        def __init__(self) -> None:
            self.closed = False
            self.protocol: str | None = "v5.channel.k8s.io"
            self.close_code: int | None = None

        async def send_bytes(self, data: bytes) -> None:
            raise ClientError("transport went away")

        async def close(self) -> None:
            self.closed = True

    fake_ws: Any = _FakeWs()
    conn = AioHttpWebSocketConnection(fake_ws)
    try:
        with pytest.raises(KubexClientException, match="send failed"):
            await conn.send_bytes(b"\x00data")
    finally:
        await conn.close()


@pytest.mark.anyio
async def test_concurrent_close_during_receive_does_not_raise_abnormal() -> None:
    """A concurrent ``close()`` must not reclassify in-flight ``receive()``.

    aiohttp breaks a waiting ``receive()`` by feeding ``WSMsgType.CLOSING`` so
    the closing task can join. Our adapter must recognise that the local
    ``close()`` initiated this teardown and treat it as clean EOF rather
    than a transport-loss event — otherwise exiting an ``async with
    api.exec.stream(...)`` block before the peer closes would spuriously
    raise from the read loop.
    """
    from kubex.client.aiohttp import AioHttpWebSocketConnection

    class _FakeMessage:
        def __init__(self, msg_type: WSMsgType) -> None:
            self.type = msg_type
            self.data: int | None = None
            self.extra: str | None = None

    class _FakeWs:
        def __init__(self) -> None:
            import anyio

            self.closed = False
            self.protocol: str | None = "v5.channel.k8s.io"
            self.close_code: int | None = 1000
            self._receive_event = anyio.Event()

        async def receive(self) -> _FakeMessage:
            await self._receive_event.wait()
            return _FakeMessage(WSMsgType.CLOSING)

        async def close(self) -> None:
            self.closed = True
            self._receive_event.set()

    import anyio

    fake_ws: Any = _FakeWs()
    conn = AioHttpWebSocketConnection(fake_ws)

    async with anyio.create_task_group() as tg:

        async def _reader() -> None:
            with pytest.raises(StopAsyncIteration):
                await conn.receive_bytes()

        tg.start_soon(_reader)
        await anyio.sleep(0.01)
        await conn.close()


@pytest.mark.anyio
async def test_receive_bytes_rejects_text_frame_as_kubex_exception() -> None:
    """A text frame on the v5 channel protocol is a server-side protocol
    violation. The adapter must reject it with ``KubexClientException``
    rather than UTF-8 encoding it into bytes that the channel decoder
    would misparse as a regular binary frame.
    """

    async def text_frame_server(request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse(protocols=["v5.channel.k8s.io"])
        await ws.prepare(request)
        await ws.send_str("\x01stdout-as-text")
        await ws.close()
        return ws

    app = web.Application()
    app.router.add_get("/ws", text_frame_server)
    server = TestServer(app)
    async with server:
        config = ClientConfiguration(url=str(server.make_url("/")))
        async with AioHttpClient(config) as client:
            request = Request(method="GET", url="/ws")
            conn = await client.connect_websocket(request, ["v5.channel.k8s.io"])
            try:
                with pytest.raises(KubexClientException, match="non-binary frame"):
                    await conn.receive_bytes()
            finally:
                await conn.close()
