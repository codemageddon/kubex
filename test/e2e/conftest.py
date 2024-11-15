from typing import AsyncGenerator, Generator

import pytest
from testcontainers.k3s import K3SContainer  # type: ignore[import-untyped]
from yaml import safe_load

from kubex import Api, Client
from kubex.client.configuration import ClientConfiguration, KubeConfig
from kubex.client.file_config import configure_from_kubeconfig
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
async def client(
    kubernetes_config: ClientConfiguration,
) -> AsyncGenerator[Client, None]:
    async with Client(configuration=kubernetes_config) as client:
        yield client


@pytest.fixture
async def tmp_namespace(
    client: Client,
) -> AsyncGenerator[Namespace, None]:
    namespace_template = Namespace(metadata=ObjectMetadata(generate_name="test-"))
    api: Api[Namespace] = Api(Namespace, client=client)
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
