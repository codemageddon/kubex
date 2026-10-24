"""``tls_server_name`` drives SNI and certificate verification on both backends."""

from __future__ import annotations

import ssl
import sys
from pathlib import Path
from typing import Iterator

import pytest
from aiohttp import web

from kubex.core.exceptions import KubexConnectionError
from kubex.core.request import Request

from ._servers import ThreadedAioServer, make_self_signed_cert
from .conftest import BackendCase, ClientFactory

_SERVER_NAME = "kubernetes.test"


@pytest.fixture
def anyio_backend(backend_case: BackendCase) -> str:
    return backend_case.runtime


@pytest.fixture(scope="module")
def certificate(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    pair = make_self_signed_cert(tmp_path_factory.mktemp("tls"), _SERVER_NAME)
    if pair is None:
        pytest.skip("openssl CLI unavailable")
    return pair


@pytest.fixture
def tls_server(
    certificate: tuple[Path, Path],
) -> Iterator[tuple[ThreadedAioServer, list[str | None]]]:
    cert, key = certificate
    sni_names: list[str | None] = []
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(cert, key)
    context.sni_callback = lambda _sock, name, _ctx: sni_names.append(name)

    async def rest(request: web.Request) -> web.Response:
        return web.json_response({"ok": True})

    async def ws(request: web.Request) -> web.WebSocketResponse:
        socket = web.WebSocketResponse(protocols=["v5.channel.k8s.io"])
        await socket.prepare(request)
        await socket.send_bytes(b"\x01hello")
        await socket.close()
        return socket

    app = web.Application()
    app.router.add_get("/rest", rest)
    app.router.add_get("/ws", ws)
    with ThreadedAioServer(app, ssl_context=context) as srv:
        yield srv, sni_names


@pytest.mark.anyio
async def test_rest_and_websocket_verify_against_tls_server_name(
    tls_server: tuple[ThreadedAioServer, list[str | None]],
    certificate: tuple[Path, Path],
    make_client: ClientFactory,
) -> None:
    srv, sni_names = tls_server
    client = make_client(
        srv.url, server_ca_file=certificate[0], tls_server_name=_SERVER_NAME
    )
    async with client:
        response = await client.request(Request("GET", "/rest"))
        assert response.status_code == 200
        conn = await client.connect_websocket(
            Request("GET", "/ws"), ["v5.channel.k8s.io"]
        )
        try:
            assert await conn.receive_bytes() == b"\x01hello"
        finally:
            await conn.close()
    assert sni_names and set(sni_names) == {_SERVER_NAME}


@pytest.mark.anyio
@pytest.mark.parametrize("server_name", [None, "other.test"])
async def test_certificate_name_mismatch_is_rejected(
    tls_server: tuple[ThreadedAioServer, list[str | None]],
    certificate: tuple[Path, Path],
    make_client: ClientFactory,
    server_name: str | None,
) -> None:
    srv, _ = tls_server
    client = make_client(
        srv.url, server_ca_file=certificate[0], tls_server_name=server_name
    )
    async with client:
        with pytest.raises(KubexConnectionError):
            await client.request(Request("GET", "/rest"))
        with pytest.raises(KubexConnectionError):
            await client.connect_websocket(Request("GET", "/ws"), ["v5.channel.k8s.io"])


def test_httpx_warns_tls_server_name_with_proxy() -> None:
    """httpcore's proxy tunnel ignores sni_hostname, so say so instead of failing TLS later."""
    from kubex.client.httpx import HttpxClient
    from kubex.client.options import ClientOptions
    from kubex.configuration import ClientConfiguration

    config = ClientConfiguration(
        url="https://10.0.0.1:6443", tls_server_name="kubernetes"
    )
    with pytest.warns(UserWarning, match="tls_server_name is not applied"):
        HttpxClient(config, ClientOptions(proxy="http://proxy.local:3128"))


def test_httpx_no_tls_server_name_proxy_warning_without_proxy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import warnings

    from kubex.client.httpx import HttpxClient
    from kubex.configuration import ClientConfiguration

    for name in ("HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy"):
        monkeypatch.delenv(name, raising=False)
    config = ClientConfiguration(
        url="https://10.0.0.1:6443", tls_server_name="kubernetes"
    )
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        HttpxClient(config)


def _clear_proxy_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    for name in (
        "HTTPS_PROXY",
        "https_proxy",
        "HTTP_PROXY",
        "http_proxy",
        "ALL_PROXY",
        "all_proxy",
        "NO_PROXY",
        "no_proxy",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("NETRC", str(tmp_path / "missing-netrc"))


def test_httpx_warns_tls_server_name_with_env_proxy(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from kubex.client.httpx import HttpxClient
    from kubex.client.options import ClientOptions
    from kubex.configuration import ClientConfiguration

    _clear_proxy_env(monkeypatch, tmp_path)
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.local:3128")
    config = ClientConfiguration(
        url="https://10.0.0.1:6443", tls_server_name="kubernetes"
    )
    with pytest.warns(UserWarning, match="tls_server_name is not applied"):
        HttpxClient(config, ClientOptions(trust_env=True))


@pytest.mark.parametrize(
    "env",
    [
        pytest.param(
            {"HTTPS_PROXY": "http://proxy.local:3128", "NO_PROXY": "10.0.0.1"},
            id="no-proxy-match",
        ),
        pytest.param(
            {"HTTPS_PROXY": "http://proxy.local:3128", "https_proxy": ""},
            id="empty-lowercase-wins",
            marks=pytest.mark.skipif(
                sys.platform == "win32",
                reason="environment variable names are case-insensitive on Windows",
            ),
        ),
    ],
)
def test_httpx_no_tls_server_name_warning_when_env_proxy_is_bypassed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, env: dict[str, str]
) -> None:
    import warnings

    from kubex.client.httpx import HttpxClient
    from kubex.client.options import ClientOptions
    from kubex.configuration import ClientConfiguration

    _clear_proxy_env(monkeypatch, tmp_path)
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    config = ClientConfiguration(
        url="https://10.0.0.1:6443", tls_server_name="kubernetes"
    )
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        HttpxClient(config, ClientOptions(trust_env=True))
