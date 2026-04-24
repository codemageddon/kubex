from __future__ import annotations

import pytest

from kubex.api import Api
from kubex.k8s.v1_35.core.v1.pod import Pod
from kubex_core.models.eviction import Eviction
from kubex_core.models.metadata import ObjectMetadata

from .conftest import StubClient

STATUS_JSON = b'{"apiVersion": "v1", "kind": "Status", "metadata": {}, "status": "Success", "code": 200}'


@pytest.mark.anyio
async def test_eviction_create_builds_correct_request() -> None:
    client = StubClient(response_content=STATUS_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    eviction = Eviction(metadata=ObjectMetadata(name="my-pod"))
    result = await api.eviction.create("my-pod", eviction)
    req = client.last_request
    assert req.method == "POST"
    assert req.url.endswith("/pods/my-pod/eviction")
    assert "namespaces/default" in req.url
    assert req.body is not None
    from kubex_core.models.status import Status

    assert isinstance(result, Status)
    assert result.status == "Success"


@pytest.mark.anyio
async def test_eviction_create_with_explicit_namespace() -> None:
    client = StubClient(response_content=STATUS_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    eviction = Eviction(metadata=ObjectMetadata(name="my-pod"))
    await api.eviction.create("my-pod", eviction, namespace="other")
    req = client.last_request
    assert "namespaces/other" in req.url


@pytest.mark.anyio
async def test_eviction_create_with_dry_run() -> None:
    client = StubClient(response_content=STATUS_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    eviction = Eviction(metadata=ObjectMetadata(name="my-pod"))
    await api.eviction.create("my-pod", eviction, dry_run=True)
    req = client.last_request
    assert req.query_params is not None
    assert req.query_params.get("dryRun") == "All"


@pytest.mark.anyio
async def test_eviction_create_with_field_manager() -> None:
    client = StubClient(response_content=STATUS_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    eviction = Eviction(metadata=ObjectMetadata(name="my-pod"))
    await api.eviction.create("my-pod", eviction, field_manager="my-manager")
    req = client.last_request
    assert req.query_params is not None
    assert req.query_params.get("fieldManager") == "my-manager"


@pytest.mark.anyio
async def test_eviction_create_serializes_eviction_body() -> None:
    client = StubClient(response_content=STATUS_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    eviction = Eviction(
        api_version="policy/v1",
        kind="Eviction",
        metadata=ObjectMetadata(name="my-pod"),
    )
    await api.eviction.create("my-pod", eviction)
    req = client.last_request
    assert req.body is not None
    import json

    body = json.loads(req.body)
    assert body["apiVersion"] == "policy/v1"
    assert body["kind"] == "Eviction"
    assert body["metadata"]["name"] == "my-pod"


@pytest.mark.anyio
async def test_eviction_create_requires_namespace_for_namespaced_resource() -> None:
    client = StubClient(response_content=STATUS_JSON)
    api: Api[Pod] = Api(Pod, client=client)
    eviction = Eviction(metadata=ObjectMetadata(name="my-pod"))
    with pytest.raises(ValueError, match="Namespace is required"):
        await api.eviction.create("my-pod", eviction)


@pytest.mark.anyio
async def test_eviction_create_returns_status_object() -> None:
    response_json = (
        b'{"apiVersion": "meta/v1", "kind": "Status",'
        b' "metadata": {}, "status": "Success", "code": 200,'
        b' "message": "pod my-pod evicted"}'
    )
    client = StubClient(response_content=response_json)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    eviction = Eviction(metadata=ObjectMetadata(name="my-pod"))
    result = await api.eviction.create("my-pod", eviction)
    from kubex_core.models.status import Status

    assert isinstance(result, Status)
    assert result.status == "Success"
    assert result.code == 200
    assert result.message == "pod my-pod evicted"
