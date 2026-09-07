from __future__ import annotations

from typing import AsyncGenerator

import pytest

pytest.importorskip("aiohttp")
pytest.importorskip("httpx")

from aiohttp import web  # noqa: E402
from aiohttp.test_utils import TestServer  # noqa: E402

from kubex.client.aiohttp import AioHttpClient  # noqa: E402
from kubex.client.httpx import HttpxClient  # noqa: E402
from kubex.configuration import ClientConfiguration  # noqa: E402
from kubex.core.request import Request  # noqa: E402


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


# A body with mixed \n and \r\n terminators, matching what a real streamed
# Kubernetes log/watch response looks like.
STREAM_BODY = b"line-one\nline-two\r\nline-three\n"
EXPECTED_LINES = ["line-one", "line-two", "line-three"]


def _make_app() -> web.Application:
    async def stream(request: web.Request) -> web.StreamResponse:
        response = web.StreamResponse(headers={"Content-Type": "text/plain"})
        await response.prepare(request)
        await response.write(STREAM_BODY)
        await response.write_eof()
        return response

    app = web.Application()
    app.router.add_get("/stream", stream)
    return app


@pytest.fixture
async def stream_server() -> AsyncGenerator[TestServer, None]:
    server = TestServer(_make_app())
    async with server:
        yield server


async def _collect_lines(client: object, request: Request) -> list[str]:
    lines = []
    async for line in client.stream_lines(request):  # type: ignore[attr-defined]
        lines.append(line)
    return lines


@pytest.mark.anyio
async def test_aiohttp_stream_lines_strips_terminators(
    stream_server: TestServer,
) -> None:
    config = ClientConfiguration(
        url=str(stream_server.make_url("/")), insecure_skip_tls_verify=True
    )
    client = AioHttpClient(config)
    async with client:
        lines = await _collect_lines(client, Request(method="GET", url="/stream"))
    assert lines == EXPECTED_LINES


@pytest.mark.anyio
async def test_httpx_stream_lines_strips_terminators(stream_server: TestServer) -> None:
    config = ClientConfiguration(
        url=str(stream_server.make_url("/")), insecure_skip_tls_verify=True
    )
    client = HttpxClient(config)
    async with client:
        lines = await _collect_lines(client, Request(method="GET", url="/stream"))
    assert lines == EXPECTED_LINES


@pytest.mark.anyio
async def test_both_backends_yield_identical_lines(stream_server: TestServer) -> None:
    config = ClientConfiguration(
        url=str(stream_server.make_url("/")), insecure_skip_tls_verify=True
    )
    aiohttp_client = AioHttpClient(config)
    httpx_client = HttpxClient(config)
    async with aiohttp_client, httpx_client:
        aiohttp_lines = await _collect_lines(
            aiohttp_client, Request(method="GET", url="/stream")
        )
        httpx_lines = await _collect_lines(
            httpx_client, Request(method="GET", url="/stream")
        )
    assert aiohttp_lines == httpx_lines == EXPECTED_LINES
