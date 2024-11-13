import base64
from pathlib import Path
from typing import AsyncGenerator, Generator

import pytest
from testcontainers.k3s import K3SContainer  # type: ignore[import-untyped]
from yaml import safe_load

from kubex import Api, Client, ClientConfiguration
from kubex.models.metadata import ObjectMetadata
from kubex.models.namespace import Namespace


@pytest.fixture(scope="session")
def kubernetes() -> Generator[K3SContainer, None, None]:
    with K3SContainer(
        enable_cgroup_mount=False,
    ) as k3s:
        yield k3s


@pytest.fixture
def kubernetes_config(
    kubernetes: K3SContainer,
    tmp_path: Path,
) -> Generator[ClientConfiguration, None, None]:
    conf = safe_load(kubernetes.config_yaml())
    current_context = conf["current-context"]
    context = next(
        context for context in conf["contexts"] if context["name"] == current_context
    )
    cluster = next(
        cluster
        for cluster in conf["clusters"]
        if cluster["name"] == context["context"]["cluster"]
    )
    user = next(
        user for user in conf["users"] if user["name"] == context["context"]["user"]
    )
    url = cluster["cluster"]["server"]
    server_ca_data = base64.b64decode(
        cluster["cluster"]["certificate-authority-data"]
    ).decode()
    user_cert_data = base64.b64decode(user["user"]["client-certificate-data"]).decode()
    user_key_data = base64.b64decode(user["user"]["client-key-data"]).decode()
    with (
        open(tmp_path / "server_ca.crt", "w") as server_ca_file,
        open(tmp_path / "client.crt", "w") as client_cert_file,
        open(tmp_path / "client.key", "w") as client_key_file,
    ):
        server_ca_file.write(server_ca_data)
        client_cert_file.write(user_cert_data)
        client_key_file.write(user_key_data)
    yield ClientConfiguration(
        url=url,
        server_ca_file=str(tmp_path / "server_ca.crt"),
        client_cert_file=str(tmp_path / "client.crt"),
        client_key_file=str(tmp_path / "client.key"),
    )


@pytest.fixture
async def client(
    kubernetes_config: ClientConfiguration,
) -> AsyncGenerator[Client, None]:
    async with Client(configuration=kubernetes_config) as client:
        yield client
    # yield Client(configuration=kubernetes_config)


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
