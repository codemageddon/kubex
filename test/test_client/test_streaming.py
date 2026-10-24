"""``stream_lines`` behaviour shared by both backends (watches and log follows)."""

from __future__ import annotations

import asyncio
import json
import socket
import time
from typing import Iterator

import pytest
from aiohttp import web

from kubex.client.client import BaseClient
from kubex.client.options import ClientOptions
from kubex.core.exceptions import (
    KubexClientException,
    KubexConnectionError,
    KubexTimeoutError,
)
from kubex.core.params import Timeout, TimeoutTypes
from kubex.core.request import Request

from ._servers import RawHttpServer, ThreadedAioServer
from .conftest import BackendCase, ClientFactory


@pytest.fixture
def anyio_backend(backend_case: BackendCase) -> str:
    return backend_case.runtime


# U+0085 (NEL) inside a JSON string must not end a line; it arrives split across
# chunks, as does a CRLF terminator and an invalid UTF-8 sequence.
_CHUNKS = [
    b'{"a": "x\xc2',
    b'\x85y"}\r',
    b"\nline\rwith-cr\n\xff\xfe",
    b"bad\nlast-no-newline",
]
_EXPECTED = ['{"a": "x\x85y"}', "line\rwith-cr", "��bad", "last-no-newline"]
_LONG_LINE = 5 * 1024 * 1024
_IDLE_GAP = 1.0


async def _chunks(request: web.Request) -> web.StreamResponse:
    response = web.StreamResponse(headers={"Content-Type": "application/json"})
    await response.prepare(request)
    for chunk in _CHUNKS:
        await response.write(chunk)
        await asyncio.sleep(0.01)
    await response.write_eof()
    return response


async def _long(request: web.Request) -> web.StreamResponse:
    response = web.StreamResponse(headers={"Content-Type": "application/json"})
    await response.prepare(request)
    piece = b"x" * 65536
    for _ in range(_LONG_LINE // len(piece)):
        await response.write(piece)
    await response.write(b"\ntail\n")
    await response.write_eof()
    return response


async def _idle(request: web.Request) -> web.StreamResponse:
    response = web.StreamResponse(headers={"Content-Type": "application/json"})
    await response.prepare(request)
    await response.write(b"one\n")
    await asyncio.sleep(_IDLE_GAP)
    await response.write(b"two\n")
    await response.write_eof()
    return response


@pytest.fixture
def server() -> Iterator[ThreadedAioServer]:
    app = web.Application()
    app.router.add_get("/chunks", _chunks)
    app.router.add_get("/long", _long)
    app.router.add_get("/idle", _idle)
    with ThreadedAioServer(app) as srv:
        yield srv


async def _collect(client: BaseClient, request: Request) -> list[str]:
    lines: list[str] = []
    async with client:
        async for line in client.stream_lines(request):
            lines.append(line)
    return lines


@pytest.mark.anyio
async def test_splits_on_newline_only_and_decodes_tolerantly(
    server: ThreadedAioServer, make_client: ClientFactory
) -> None:
    lines = await _collect(make_client(server.url), Request("GET", "/chunks"))
    assert lines == _EXPECTED
    assert json.loads(lines[0]) == {"a": "x\x85y"}


@pytest.mark.anyio
async def test_long_line_has_no_buffer_cap(
    server: ThreadedAioServer, make_client: ClientFactory, backend_case: BackendCase
) -> None:
    # A tiny aiohttp read buffer used to cap lines at 2x its size (LineTooLong).
    options = (
        ClientOptions(buffer_size=1024) if backend_case.client == "aiohttp" else None
    )
    lines = await _collect(make_client(server.url, options), Request("GET", "/long"))
    assert [len(line) for line in lines] == [_LONG_LINE, 4]


@pytest.mark.anyio
@pytest.mark.parametrize(
    "client_timeout",
    [pytest.param(..., id="library-default"), pytest.param(0.3, id="numeric")],
)
async def test_client_default_timeout_does_not_bound_idle_stream(
    server: ThreadedAioServer,
    make_client: ClientFactory,
    client_timeout: float,
) -> None:
    options = ClientOptions(timeout=client_timeout)
    lines = await _collect(make_client(server.url, options), Request("GET", "/idle"))
    assert lines == ["one", "two"]


@pytest.mark.anyio
@pytest.mark.parametrize(
    "request_timeout",
    [
        pytest.param(Timeout(read=0.3), id="read"),
        pytest.param(0.3, id="numeric"),
    ],
)
async def test_explicit_request_timeout_still_bounds_stream(
    server: ThreadedAioServer,
    make_client: ClientFactory,
    request_timeout: TimeoutTypes,
) -> None:
    lines: list[str] = []
    client = make_client(server.url)
    with pytest.raises(KubexTimeoutError) as exc_info:
        async with client:
            async for line in client.stream_lines(
                Request("GET", "/idle", timeout=request_timeout)
            ):
                lines.append(line)
    assert lines == ["one"]
    assert isinstance(exc_info.value, TimeoutError)


def _truncated_chunked(sock: socket.socket) -> None:
    sock.sendall(
        b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n"
        b"Transfer-Encoding: chunked\r\n\r\n6\r\nline1\n\r\n"
    )
    time.sleep(0.3)


@pytest.mark.anyio
async def test_connection_lost_mid_stream_raises_kubex_connection_error(
    make_client: ClientFactory,
) -> None:
    lines: list[str] = []
    with RawHttpServer(_truncated_chunked) as srv:
        client = make_client(srv.url)
        with pytest.raises(KubexConnectionError):
            async with client:
                async for line in client.stream_lines(Request("GET", "/watch")):
                    lines.append(line)
    assert lines == ["line1"]


@pytest.mark.anyio
async def test_connection_refused_raises_kubex_connection_error(
    make_client: ClientFactory,
) -> None:
    client = make_client("http://127.0.0.1:1")
    with pytest.raises(KubexConnectionError) as exc_info:
        await _collect(client, Request("GET", "/watch"))
    assert isinstance(exc_info.value, KubexClientException)
    assert exc_info.value.__cause__ is not None
