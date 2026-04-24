from __future__ import annotations

import pytest

from kubex.core.params import PostOptions
from kubex.core.request_builder.builder import RequestBuilder
from kubex_core.models.resource_config import ResourceConfig, Scope


@pytest.fixture()
def builder() -> RequestBuilder:
    rc: ResourceConfig = ResourceConfig(  # type: ignore[type-arg]
        version="v1",
        kind="Pod",
        plural="pods",
        scope=Scope.NAMESPACE,
        group="core",
    )
    return RequestBuilder(rc)


def test_create_subresource_post_method(builder: RequestBuilder) -> None:
    request = builder.create_subresource(
        "eviction",
        "my-pod",
        "default",
        data='{"apiVersion":"policy/v1","kind":"Eviction"}',
        options=PostOptions(),
    )
    assert request.method == "POST"


def test_create_subresource_url(builder: RequestBuilder) -> None:
    request = builder.create_subresource(
        "eviction",
        "my-pod",
        "default",
        data='{"apiVersion":"policy/v1","kind":"Eviction"}',
        options=PostOptions(),
    )
    assert request.url == "/api/v1/namespaces/default/pods/my-pod/eviction"


def test_create_subresource_body(builder: RequestBuilder) -> None:
    body = '{"apiVersion":"policy/v1","kind":"Eviction"}'
    request = builder.create_subresource(
        "eviction",
        "my-pod",
        "default",
        data=body,
        options=PostOptions(),
    )
    assert request.body == body


def test_create_subresource_query_params_from_options(builder: RequestBuilder) -> None:
    options = PostOptions(dry_run=True, field_manager="test-manager")
    request = builder.create_subresource(
        "eviction",
        "my-pod",
        "default",
        data="{}",
        options=options,
    )
    assert request.query_params == {"dryRun": "All", "fieldManager": "test-manager"}


def test_create_subresource_no_query_params_when_default_options(
    builder: RequestBuilder,
) -> None:
    request = builder.create_subresource(
        "eviction",
        "my-pod",
        "default",
        data="{}",
        options=PostOptions(),
    )
    assert request.query_params is None


def test_create_subresource_timeout(builder: RequestBuilder) -> None:
    request = builder.create_subresource(
        "eviction",
        "my-pod",
        "default",
        data="{}",
        options=PostOptions(),
        request_timeout=30,
    )
    timeout = request.timeout
    assert timeout is not None
    assert timeout is not Ellipsis
    assert timeout.total == 30


def test_create_subresource_default_timeout_is_ellipsis(
    builder: RequestBuilder,
) -> None:
    request = builder.create_subresource(
        "eviction",
        "my-pod",
        "default",
        data="{}",
        options=PostOptions(),
    )
    assert request.timeout is Ellipsis


def test_create_subresource_cluster_scoped() -> None:
    rc: ResourceConfig = ResourceConfig(  # type: ignore[type-arg]
        version="v1",
        kind="Node",
        plural="nodes",
        scope=Scope.CLUSTER,
        group="core",
    )
    builder = RequestBuilder(rc)
    request = builder.create_subresource(
        "eviction",
        "my-node",
        None,
        data="{}",
        options=PostOptions(),
    )
    assert request.url == "/api/v1/nodes/my-node/eviction"
