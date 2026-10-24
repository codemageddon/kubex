"""WebSocket keepalive and adapter error normalisation on both backends."""

from __future__ import annotations

import asyncio
from contextlib import AbstractAsyncContextManager
from typing import Any, Iterator

import anyio
import pytest
from aiohttp import WSMsgType, web

from kubex.core.exceptions import KubexClientException
from kubex.core.request import Request

from ._servers import ThreadedAioServer
from .conftest import BackendCase, ClientFactory

_PAUSE = 0.8


@pytest.fixture
def anyio_backend(backend_case: BackendCase) -> str:
    return backend_case.runtime


@pytest.fixture
def unanswered_pings() -> Iterator[tuple[ThreadedAioServer, list[int]]]:
    """A server that counts client pings, never answers them, then sends a frame."""
    pings: list[int] = []

    async def ws(request: web.Request) -> web.WebSocketResponse:
        socket = web.WebSocketResponse(protocols=["v5.channel.k8s.io"], autoping=False)
        await socket.prepare(request)
        loop = asyncio.get_running_loop()
        deadline = loop.time() + _PAUSE - 0.2
        while (remaining := deadline - loop.time()) > 0:
            try:
                msg = await socket.receive(timeout=remaining)
            except asyncio.TimeoutError:
                break
            if msg.type == WSMsgType.PING:
                pings.append(1)
            elif msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSING, WSMsgType.CLOSED):
                return socket
        await socket.send_bytes(b"\x01done")
        await socket.close()
        return socket

    app = web.Application()
    app.router.add_get("/ws", ws)
    with ThreadedAioServer(app) as srv:
        yield srv, pings


@pytest.mark.anyio
async def test_pings_are_sent_without_a_pong_deadline(
    unanswered_pings: tuple[ThreadedAioServer, list[int]],
    make_client: ClientFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A consumer that stops reading (backpressure) never processes pongs; the
    # connection must survive a pause much longer than the ping interval.
    monkeypatch.setattr("kubex.client.httpx.WS_PING_INTERVAL_SECONDS", 0.05)
    monkeypatch.setattr("kubex.client.aiohttp.WS_PING_INTERVAL_SECONDS", 0.05)
    srv, pings = unanswered_pings
    async with make_client(srv.url) as client:
        conn = await client.connect_websocket(
            Request("GET", "/ws"), ["v5.channel.k8s.io"]
        )
        try:
            await anyio.sleep(_PAUSE)
            assert await conn.receive_bytes() == b"\x01done"
        finally:
            await conn.close()
    assert len(pings) >= 3


class _Boom(RuntimeError):
    pass


@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio", "trio"])
@pytest.mark.parametrize("operation", ["send", "receive", "close"])
async def test_httpx_adapter_normalises_unexpected_errors(operation: str) -> None:
    from wsproto.utilities import LocalProtocolError

    from kubex.client.httpx import HttpxWebSocketConnection

    class _Session:
        subprotocol = "v5.channel.k8s.io"

        async def send_bytes(self, data: bytes) -> None:
            raise LocalProtocolError("Connection cannot be closed in state CLOSED")

        async def receive_bytes(self) -> bytes:
            raise _Boom("receive")

    class _Cm(AbstractAsyncContextManager[Any]):
        async def __aexit__(self, *exc_info: object) -> None:
            raise _Boom("close")

    conn = HttpxWebSocketConnection(_Cm(), _Session())  # type: ignore[arg-type]
    with pytest.raises(KubexClientException) as exc_info:
        match operation:
            case "send":
                await conn.send_bytes(b"\x00x")
            case "receive":
                await conn.receive_bytes()
            case _:
                await conn.close()
    assert exc_info.value.__cause__ is not None


@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio"])
@pytest.mark.parametrize("operation", ["send", "receive", "close"])
async def test_aiohttp_adapter_normalises_unexpected_errors(operation: str) -> None:
    from kubex.client.aiohttp import AioHttpWebSocketConnection

    class _Ws:
        closed = False
        protocol = "v5.channel.k8s.io"

        async def send_bytes(self, data: bytes) -> None:
            raise _Boom("send")

        async def receive(self) -> Any:
            raise _Boom("receive")

        async def close(self) -> None:
            raise _Boom("close")

    conn = AioHttpWebSocketConnection(_Ws())  # type: ignore[arg-type]
    with pytest.raises(KubexClientException) as exc_info:
        match operation:
            case "send":
                await conn.send_bytes(b"\x00x")
            case "receive":
                await conn.receive_bytes()
            case _:
                await conn.close()
    assert isinstance(exc_info.value.__cause__, _Boom)
