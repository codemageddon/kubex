"""Transport failures surface as kubex exceptions on both backends."""

from __future__ import annotations

import json
import socket
import time
from typing import Iterator

import anyio
import pytest
from aiohttp import web

from kubex.client.options import ClientOptions
from kubex.core.exceptions import (
    Forbidden,
    KubexApiError,
    KubexClientException,
    KubexConnectionError,
    KubexTimeoutError,
    NotFound,
)
from kubex.core.request import Request
from kubex_core.models.status import Status

from ._servers import RawHttpServer, ThreadedAioServer
from .conftest import BackendCase, ClientFactory

_SUBPROTOCOLS = ["v5.channel.k8s.io"]


@pytest.fixture
def anyio_backend(backend_case: BackendCase) -> str:
    return backend_case.runtime


def _trickle(sock: socket.socket) -> None:
    """A response whose body arrives one byte every 100 ms (5 s in total)."""
    sock.sendall(
        b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n"
        b"Content-Length: 50\r\n\r\n"
    )
    for _ in range(50):
        time.sleep(0.1)
        sock.sendall(b" ")


@pytest.mark.anyio
async def test_connection_refused_raises_kubex_connection_error(
    make_client: ClientFactory,
) -> None:
    async with make_client("http://127.0.0.1:1") as client:
        with pytest.raises(KubexConnectionError) as exc_info:
            await client.request(Request("GET", "/api/v1/pods"))
    assert exc_info.value.__cause__ is not None


@pytest.mark.anyio
@pytest.mark.parametrize("where", ["request", "client"])
async def test_numeric_timeout_is_a_total_bound(
    make_client: ClientFactory, where: str
) -> None:
    # Each byte arrives well within any per-phase read timeout; only a
    # wall-clock total stops the request.
    options = ClientOptions(timeout=0.5) if where == "client" else None
    request = Request("GET", "/slow", timeout=0.5 if where == "request" else ...)
    with RawHttpServer(_trickle) as srv:
        async with make_client(srv.url, options) as client:
            started = time.monotonic()
            with pytest.raises(KubexTimeoutError) as exc_info:
                await client.request(request)
            elapsed = time.monotonic() - started
    assert isinstance(exc_info.value, TimeoutError)
    assert elapsed < 2.5


@pytest.mark.anyio
async def test_outer_cancellation_is_not_converted(make_client: ClientFactory) -> None:
    with RawHttpServer(_trickle) as srv:
        async with make_client(srv.url) as client:
            with anyio.move_on_after(0.3) as scope:
                await client.request(Request("GET", "/slow", timeout=None))
    assert scope.cancelled_caught


async def _forbidden(request: web.Request) -> web.Response:
    body = {
        "kind": "Status",
        "apiVersion": "v1",
        "status": "Failure",
        "message": 'pods "x" is forbidden: cannot create resource "pods/exec"',
        "reason": "Forbidden",
        "code": 403,
    }
    return web.json_response(body, status=403)


async def _not_found(request: web.Request) -> web.Response:
    return web.Response(status=404, text="404 page not found")


async def _ok(request: web.Request) -> web.Response:
    return web.json_response({})


@pytest.fixture
def handshake_server() -> Iterator[ThreadedAioServer]:
    app = web.Application()
    app.router.add_get("/forbidden", _forbidden)
    app.router.add_get("/missing", _not_found)
    app.router.add_get("/plain", _ok)
    with ThreadedAioServer(app) as srv:
        yield srv


@pytest.mark.anyio
async def test_websocket_handshake_403_raises_forbidden_with_status(
    handshake_server: ThreadedAioServer, make_client: ClientFactory
) -> None:
    async with make_client(handshake_server.url) as client:
        with pytest.raises(Forbidden) as exc_info:
            await client.connect_websocket(Request("GET", "/forbidden"), _SUBPROTOCOLS)
    content = exc_info.value.content
    assert isinstance(content, Status)
    assert content.message is not None and "pods/exec" in content.message
    assert "pods/exec" in str(exc_info.value)


@pytest.mark.anyio
async def test_websocket_handshake_404_raises_not_found(
    handshake_server: ThreadedAioServer, make_client: ClientFactory
) -> None:
    async with make_client(handshake_server.url) as client:
        with pytest.raises(NotFound) as exc_info:
            await client.connect_websocket(Request("GET", "/missing"), _SUBPROTOCOLS)
    assert exc_info.value.content == "404 page not found"


@pytest.mark.anyio
async def test_websocket_handshake_non_error_status_is_client_exception(
    handshake_server: ThreadedAioServer, make_client: ClientFactory
) -> None:
    async with make_client(handshake_server.url) as client:
        with pytest.raises(KubexClientException, match="handshake failed") as exc_info:
            await client.connect_websocket(Request("GET", "/plain"), _SUBPROTOCOLS)
    assert not isinstance(exc_info.value, KubexApiError)


@pytest.mark.anyio
async def test_websocket_connection_refused_raises_kubex_connection_error(
    make_client: ClientFactory,
) -> None:
    async with make_client("http://127.0.0.1:1") as client:
        with pytest.raises(KubexConnectionError, match="connection failed"):
            await client.connect_websocket(Request("GET", "/ws"), _SUBPROTOCOLS)


@pytest.mark.anyio
async def test_rejected_upgrade_body_is_not_kept_for_regular_requests(
    handshake_server: ThreadedAioServer, make_client: ClientFactory
) -> None:
    # The body-capture hook only engages during a WebSocket upgrade; regular
    # REST errors keep going through the normal response path.
    async with make_client(handshake_server.url) as client:
        with pytest.raises(Forbidden) as exc_info:
            await client.request(Request("GET", "/forbidden"))
    assert isinstance(exc_info.value.content, Status)
    assert json.loads(exc_info.value.content.model_dump_json())["code"] == 403
