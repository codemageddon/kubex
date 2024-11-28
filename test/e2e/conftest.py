from typing import AsyncGenerator, Generator

import pytest
from testcontainers.k3s import K3SContainer  # type: ignore[import-untyped]
from yaml import safe_load

from kubex import Api
from kubex.client.aiohttp import AioHttpClient
from kubex.client.client import BaseClient, ClientChoise, create_client
from kubex.client.httpx import HttpxClient
from kubex.configuration.configuration import ClientConfiguration, KubeConfig
from kubex.configuration.file_config import configure_from_kubeconfig
from kubex.models.metadata import ObjectMetadata
from kubex.models.namespace import Namespace


@pytest.fixture(scope="session")
def kubernetes() -> Generator[K3SContainer, None, None]:
    with K3SContainer(
        enable_cgroup_mount=False,
    ) as k3s:
        yield k3s


@pytest.fixture
async def kubernetes_config(
    kubernetes: K3SContainer,
) -> AsyncGenerator[ClientConfiguration, None]:
    conf = safe_load(kubernetes.config_yaml())
    config = KubeConfig.model_validate(conf)
    client_config = await configure_from_kubeconfig(config)
    yield client_config


@pytest.fixture
async def httpx_client(
    kubernetes_config: ClientConfiguration,
) -> AsyncGenerator[HttpxClient, None]:
    async with HttpxClient(kubernetes_config) as client:
        yield client


@pytest.fixture
async def aiohttp_client(
    kubernetes_config: ClientConfiguration,
) -> AsyncGenerator[AioHttpClient, None]:
    async with AioHttpClient(kubernetes_config) as client:
        yield client


@pytest.fixture(
    params=[
        ClientChoise.HTTPX,
        ClientChoise.AIOHTTP,
    ]
)
async def client(
    kubernetes_config: ClientConfiguration,
    request: pytest.FixtureRequest,
    anyio_backend: str,
) -> AsyncGenerator[BaseClient, None]:
    if anyio_backend == "trio" and request.param != ClientChoise.HTTPX:
        pytest.skip("Skipping AIOHTTP client for trio backend")
    client = await create_client(kubernetes_config, request.param)
    async with client as client:
        yield client


@pytest.fixture
async def tmp_namespace(
    httpx_client: HttpxClient,
) -> AsyncGenerator[Namespace, None]:
    namespace_template = Namespace(metadata=ObjectMetadata(generate_name="test-"))
    api: Api[Namespace] = Api(Namespace, client=httpx_client)
    namespace = await api.create(namespace_template)
    assert namespace.metadata.name is not None
    yield namespace
    await api.delete(namespace.metadata.name)


@pytest.fixture
def tmp_namespace_name(
    tmp_namespace: Namespace,
) -> Generator[str, None, None]:
    assert tmp_namespace.metadata.name is not None
    yield tmp_namespace.metadata.name
