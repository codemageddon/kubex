"""Proxy credentials in ``ClientOptions.proxy`` never reach aiohttp's URL handling.

aiohttp puts a proxy URL's userinfo into ``ClientHttpProxyError``'s message, so
the backend strips it and sends ``Proxy-Authorization`` itself.
"""

from __future__ import annotations

import asyncio
import warnings
from base64 import b64encode
from typing import AsyncIterator

import pytest

pytest.importorskip("aiohttp")

from kubex.client.aiohttp import AioHttpClient, _split_proxy_credentials  # noqa: E402
from kubex.client.options import ClientOptions  # noqa: E402
from kubex.configuration import ClientConfiguration  # noqa: E402
from kubex.core.exceptions import Forbidden, KubexConnectionError  # noqa: E402
from kubex.core.request import Request  # noqa: E402

_PASSWORD = "s3cret"
_EXPECTED_HEADER = "Basic " + b64encode(f"alice:{_PASSWORD}".encode()).decode()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.parametrize(
    ("proxy", "expected_url", "expected_userpass"),
    [
        pytest.param("http://proxy:3128", "http://proxy:3128", None, id="no-userinfo"),
        pytest.param(
            "http://alice:s3cret@proxy:3128",
            "http://proxy:3128",
            "alice:s3cret",
            id="user-and-password",
        ),
        pytest.param(
            "http://alice@proxy:3128", "http://proxy:3128", "alice:", id="user-only"
        ),
        pytest.param(
            "http://alice:p%40ss@proxy:3128",
            "http://proxy:3128",
            "alice:p@ss",
            id="percent-encoded",
        ),
        pytest.param(
            "http://alice:p@ss@proxy:3128",
            "http://proxy:3128",
            "alice:p@ss",
            id="raw-at-in-password",
        ),
    ],
)
def test_split_proxy_credentials(
    proxy: str, expected_url: str, expected_userpass: str | None
) -> None:
    url, authorization = _split_proxy_credentials(proxy)
    assert url == expected_url
    if expected_userpass is None:
        assert authorization is None
    else:
        assert (
            authorization == "Basic " + b64encode(expected_userpass.encode()).decode()
        )


@pytest.mark.anyio
@pytest.mark.parametrize(
    "proxy",
    [
        pytest.param("http://alice:s3cret@proxy:3128", id="str"),
        pytest.param({"https": "http://alice:s3cret@proxy:3128"}, id="dict"),
    ],
)
async def test_session_proxy_has_no_userinfo(proxy: str | dict[str, str]) -> None:
    client = AioHttpClient(
        ClientConfiguration(url="https://kube.invalid"), ClientOptions(proxy=proxy)
    )
    assert client._session_kwargs()["proxy"] == "http://proxy:3128"
    assert client._transport_kwargs()["proxy_headers"] == {
        "Proxy-Authorization": _EXPECTED_HEADER
    }


class _RejectingProxy:
    """Records each request head and answers 403 (to CONNECT and plain requests)."""

    def __init__(self) -> None:
        self.heads: list[str] = []
        self.url = ""

    async def _handle(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        try:
            self.heads.append((await reader.readuntil(b"\r\n\r\n")).decode())
            writer.write(
                b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\n"
                b"Connection: close\r\n\r\n"
            )
            await writer.drain()
        finally:
            writer.close()

    def proxy_authorization(self) -> list[str]:
        return [
            line.partition(":")[2].strip()
            for head in self.heads
            for line in head.split("\r\n")
            if line.lower().startswith("proxy-authorization:")
        ]


@pytest.fixture
async def rejecting_proxy() -> AsyncIterator[_RejectingProxy]:
    proxy = _RejectingProxy()
    server = await asyncio.start_server(proxy._handle, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    proxy.url = f"http://alice:{_PASSWORD}@127.0.0.1:{port}"
    async with server:
        yield proxy


def _client(origin: str, proxy: _RejectingProxy) -> AioHttpClient:
    return AioHttpClient(
        ClientConfiguration(url=origin, insecure_skip_tls_verify=True),
        ClientOptions(proxy=proxy.url),
    )


def _assert_no_password(exc: BaseException) -> None:
    current: BaseException | None = exc
    while current is not None:
        assert _PASSWORD not in str(current)
        current = current.__cause__


@pytest.mark.anyio
@pytest.mark.parametrize("call", ["request", "stream_lines"])
async def test_refused_connect_error_omits_proxy_password(
    rejecting_proxy: _RejectingProxy, call: str
) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        async with _client("https://kube.invalid:6443", rejecting_proxy) as client:
            with pytest.raises(KubexConnectionError) as exc_info:
                if call == "request":
                    await client.request(Request("GET", "/api/v1/pods"))
                else:
                    async for _ in client.stream_lines(Request("GET", "/api/v1/pods")):
                        pass
    _assert_no_password(exc_info.value)
    assert rejecting_proxy.heads[0].startswith("CONNECT kube.invalid:6443 ")
    assert rejecting_proxy.proxy_authorization() == [_EXPECTED_HEADER]


@pytest.mark.anyio
@pytest.mark.parametrize(
    "timeout",
    [pytest.param(..., id="session"), pytest.param(5, id="temporary-session")],
)
async def test_refused_websocket_connect_error_omits_proxy_password(
    rejecting_proxy: _RejectingProxy, timeout: float
) -> None:
    async with _client("https://kube.invalid:6443", rejecting_proxy) as client:
        with pytest.raises(KubexConnectionError) as exc_info:
            await client.connect_websocket(
                Request("GET", "/api/v1/pods/p/exec", timeout=timeout),
                ["v5.channel.k8s.io"],
            )
    _assert_no_password(exc_info.value)
    assert rejecting_proxy.proxy_authorization() == [_EXPECTED_HEADER]


@pytest.mark.anyio
async def test_plain_http_origin_sends_credentials_to_proxy(
    rejecting_proxy: _RejectingProxy,
) -> None:
    async with _client("http://kube.invalid:8080", rejecting_proxy) as client:
        with pytest.raises(Forbidden):
            await client.request(Request("GET", "/api/v1/pods"))
    assert rejecting_proxy.heads[0].startswith("GET http://kube.invalid:8080/")
    assert rejecting_proxy.proxy_authorization() == [_EXPECTED_HEADER]
