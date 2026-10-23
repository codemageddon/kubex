from __future__ import annotations

from typing import AsyncGenerator

import pytest

pytest.importorskip("aiohttp")

from aiohttp import web  # noqa: E402
from aiohttp.test_utils import TestServer  # noqa: E402

from kubex.client.aiohttp import AioHttpClient, _split_base_url  # noqa: E402
from kubex.configuration import ClientConfiguration  # noqa: E402
from kubex.core.request import Request  # noqa: E402


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.parametrize(
    ("base_url", "expected_origin", "expected_prefix"),
    [
        ("https://host:6443", "https://host:6443", ""),
        ("https://host:6443/", "https://host:6443", ""),
        ("https://host/kubernetes", "https://host", "/kubernetes"),
        ("https://host/kubernetes/", "https://host", "/kubernetes"),
        ("https://host/k8s/clusters/c-xxxxx/", "https://host", "/k8s/clusters/c-xxxxx"),
    ],
)
def test_split_base_url(
    base_url: str, expected_origin: str, expected_prefix: str
) -> None:
    origin, prefix = _split_base_url(base_url)
    assert origin == expected_origin
    assert prefix == expected_prefix


def _make_gateway_app() -> web.Application:
    async def get_pod(request: web.Request) -> web.Response:
        return web.json_response({"path": request.path})

    app = web.Application()
    app.router.add_get("/gateway/api/v1/namespaces/ns/pods/my-pod", get_pod)
    return app


@pytest.fixture
async def gateway_server() -> AsyncGenerator[TestServer, None]:
    server = TestServer(_make_gateway_app())
    async with server:
        yield server


@pytest.mark.anyio
async def test_request_preserves_gateway_path_prefix(
    gateway_server: TestServer,
) -> None:
    """A server URL with its own path component (e.g. a Rancher-style gateway)
    must not lose that prefix — this used to 404 on the aiohttp backend.
    """
    base_url = str(gateway_server.make_url("/gateway/"))
    config = ClientConfiguration(url=base_url, insecure_skip_tls_verify=True)
    client = AioHttpClient(config)
    async with client:
        response = await client.request(
            Request(method="GET", url="/api/v1/namespaces/ns/pods/my-pod")
        )
    assert response.status_code == 200
    assert response.content == b'{"path": "/gateway/api/v1/namespaces/ns/pods/my-pod"}'
