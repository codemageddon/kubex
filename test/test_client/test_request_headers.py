"""Headers kubex sends (impersonation) and reads (``Warning``) on both backends."""

from __future__ import annotations

import warnings
from typing import Iterator

import pytest
from aiohttp import web
from multidict import CIMultiDict

from kubex.core.request import Request

from ._servers import ThreadedAioServer
from .conftest import BackendCase, ClientFactory


@pytest.fixture
def anyio_backend(backend_case: BackendCase) -> str:
    return backend_case.runtime


_IMPERSONATION = {
    "token": "secret-token",
    "impersonate_user": "alice",
    "impersonate_uid": "uid-1",
    "impersonate_groups": ["devs", "ops"],
    "impersonate_extra": {"scopes": ["view", "edit"]},
}
_EXPECTED_HEADERS = {
    "Authorization": ["Bearer secret-token"],
    "Impersonate-User": ["alice"],
    "Impersonate-Uid": ["uid-1"],
    "Impersonate-Group": ["devs", "ops"],
    "Impersonate-Extra-scopes": ["view", "edit"],
}

_WARNINGS = [
    '299 - "extensions/v1beta1 Ingress is deprecated in v1.14+, unavailable in v1.22+"',
    '299 - "first, with a comma", 299 kube-apiserver "second \\"quoted\\""',
]
_EXPECTED_WARNINGS = [
    "API Warning: extensions/v1beta1 Ingress is deprecated in v1.14+, unavailable in v1.22+",
    "API Warning: first, with a comma",
    'API Warning: second "quoted"',
]


@pytest.fixture
def server() -> Iterator[tuple[ThreadedAioServer, list[CIMultiDict[str]]]]:
    seen: list[CIMultiDict[str]] = []

    def _capture(request: web.Request) -> None:
        seen.append(CIMultiDict(request.headers))

    async def rest(request: web.Request) -> web.Response:
        _capture(request)
        headers: CIMultiDict[str] = CIMultiDict(
            [("Warning", value) for value in _WARNINGS]
        )
        return web.json_response({}, headers=headers)

    async def stream(request: web.Request) -> web.StreamResponse:
        _capture(request)
        response = web.StreamResponse(
            headers=CIMultiDict(
                [("Content-Type", "application/json")]
                + [("Warning", value) for value in _WARNINGS]
            )
        )
        await response.prepare(request)
        await response.write(b"{}\n")
        await response.write_eof()
        return response

    async def ws(request: web.Request) -> web.WebSocketResponse:
        _capture(request)
        socket = web.WebSocketResponse(protocols=["v5.channel.k8s.io"])
        await socket.prepare(request)
        await socket.close()
        return socket

    app = web.Application()
    app.router.add_get("/rest", rest)
    app.router.add_get("/stream", stream)
    app.router.add_get("/ws", ws)
    with ThreadedAioServer(app) as srv:
        yield srv, seen


def _assert_impersonation(headers: CIMultiDict[str]) -> None:
    for name, values in _EXPECTED_HEADERS.items():
        assert headers.getall(name, []) == values, name


@pytest.mark.anyio
async def test_impersonation_headers_sent_on_rest_stream_and_websocket(
    server: tuple[ThreadedAioServer, list[CIMultiDict[str]]],
    make_client: ClientFactory,
) -> None:
    srv, seen = server
    async with make_client(srv.url, **_IMPERSONATION) as client:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            await client.request(Request("GET", "/rest"))
            async for _ in client.stream_lines(Request("GET", "/stream")):
                pass
        conn = await client.connect_websocket(
            Request("GET", "/ws"), ["v5.channel.k8s.io"]
        )
        await conn.close()
    assert len(seen) == 3
    for headers in seen:
        _assert_impersonation(headers)


@pytest.mark.anyio
async def test_non_ascii_impersonation_values_sent_as_utf8(
    server: tuple[ThreadedAioServer, list[CIMultiDict[str]]],
    make_client: ClientFactory,
) -> None:
    srv, seen = server
    async with make_client(
        srv.url, token="t", impersonate_user="józef", impersonate_groups=["équipe"]
    ) as client:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            await client.request(Request("GET", "/rest"))
        conn = await client.connect_websocket(
            Request("GET", "/ws"), ["v5.channel.k8s.io"]
        )
        await conn.close()
    assert len(seen) == 2
    for headers in seen:
        assert headers.getall("Impersonate-User") == ["józef"]
        assert headers.getall("Impersonate-Group") == ["équipe"]


@pytest.mark.anyio
async def test_request_header_overrides_client_header(
    server: tuple[ThreadedAioServer, list[CIMultiDict[str]]],
    make_client: ClientFactory,
) -> None:
    srv, seen = server
    async with make_client(srv.url, **_IMPERSONATION) as client:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            await client.request(
                Request("GET", "/rest", headers={"Impersonate-User": "bob"})
            )
    assert seen[0].getall("Impersonate-User") == ["bob"]
    assert seen[0].getall("Impersonate-Group") == ["devs", "ops"]


@pytest.mark.anyio
async def test_warning_headers_parsed_per_rfc7234(
    server: tuple[ThreadedAioServer, list[CIMultiDict[str]]],
    make_client: ClientFactory,
) -> None:
    srv, _ = server
    async with make_client(srv.url) as client:
        with warnings.catch_warnings(record=True) as rest_caught:
            warnings.simplefilter("always")
            await client.request(Request("GET", "/rest"))
        with warnings.catch_warnings(record=True) as stream_caught:
            warnings.simplefilter("always")
            async for _ in client.stream_lines(Request("GET", "/stream")):
                pass
    for caught in (rest_caught, stream_caught):
        messages = [str(w.message) for w in caught if w.category is UserWarning]
        assert messages == _EXPECTED_WARNINGS
