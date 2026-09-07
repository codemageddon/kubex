from __future__ import annotations

import pytest

from kubex.api import Api, create_api
from kubex.configuration import ClientConfiguration
from kubex.k8s.v1_35.core.v1.namespace import Namespace
from kubex.k8s.v1_35.core.v1.pod import Pod
from test.stub_client import StubClient


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _client(namespace: str | None = None) -> StubClient:
    return StubClient(
        ClientConfiguration(
            url="https://example.invalid",
            insecure_skip_tls_verify=True,
            namespace=namespace,
        )
    )


def test_client_configuration_namespace_defaults_to_none() -> None:
    config = ClientConfiguration(url="https://example.invalid")
    assert config.namespace is None


def test_omitted_namespace_stays_none_when_configuration_unset() -> None:
    """The common case: no configured namespace must not narrow list()/watch() scope."""
    api = Api(Pod, client=_client())
    assert api._namespace is None


def test_omitted_namespace_seeds_from_configuration_for_namespace_scoped() -> None:
    api = Api(Pod, client=_client("pod-namespace"))
    assert api._namespace == "pod-namespace"


def test_explicit_none_overrides_configured_namespace() -> None:
    """Explicit namespace=None still means "all namespaces", even if configured."""
    api = Api(Pod, client=_client("pod-namespace"), namespace=None)
    assert api._namespace is None


def test_explicit_namespace_overrides_configured_namespace() -> None:
    api = Api(Pod, client=_client("pod-namespace"), namespace="other-ns")
    assert api._namespace == "other-ns"


def test_cluster_scoped_resource_never_seeded_from_configuration() -> None:
    api = Api(Namespace, client=_client("pod-namespace"))
    assert api._namespace is None


def test_cluster_scoped_resource_explicit_namespace_still_raises() -> None:
    with pytest.raises(ValueError, match="cluster-scoped"):
        Api(Namespace, client=_client("pod-namespace"), namespace="some-ns")


@pytest.mark.anyio
async def test_create_api_omitted_namespace_seeds_from_configuration() -> None:
    api = await create_api(Pod, client=_client("pod-namespace"))
    assert api._namespace == "pod-namespace"


@pytest.mark.anyio
async def test_create_api_cluster_scoped_never_seeded() -> None:
    api = await create_api(Namespace, client=_client("pod-namespace"))
    assert api._namespace is None
