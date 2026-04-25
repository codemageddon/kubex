from __future__ import annotations

import pytest

from kubex.core.request_builder.builder import RequestBuilder
from kubex_core.models.resource_config import ResourceConfig, Scope


@pytest.fixture()
def ns_builder() -> RequestBuilder:
    rc: ResourceConfig = ResourceConfig(  # type: ignore[type-arg]
        version="v1",
        kind="Pod",
        plural="pods",
        scope=Scope.NAMESPACE,
        group="core",
    )
    return RequestBuilder(rc)


@pytest.fixture()
def cluster_builder() -> RequestBuilder:
    rc: ResourceConfig = ResourceConfig(  # type: ignore[type-arg]
        version="v1",
        kind="Node",
        plural="nodes",
        scope=Scope.CLUSTER,
        group="core",
    )
    return RequestBuilder(rc)
