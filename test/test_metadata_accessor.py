from __future__ import annotations

import json

import pytest

from kubex.api import Api
from kubex.core.params import FieldValidation, Timeout
from kubex.core.patch import MergePatch, StrategicMergePatch
from kubex.k8s.v1_35.core.v1.node import Node
from kubex.k8s.v1_35.core.v1.pod import Pod
from kubex_core.models.partial_object_meta import PartialObjectMetadata
from kubex_core.models.watch_event import EventType, WatchEvent
from test.stub_client import StubClient


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


PARTIAL_META_JSON = json.dumps(
    {
        "apiVersion": "meta.k8s.io/v1",
        "kind": "PartialObjectMetadata",
        "metadata": {"name": "my-pod", "namespace": "default"},
    }
).encode()

PARTIAL_META_LIST_JSON = json.dumps(
    {
        "apiVersion": "meta.k8s.io/v1",
        "kind": "PartialObjectMetadataList",
        "metadata": {"resourceVersion": "100"},
        "items": [
            {
                "apiVersion": "meta.k8s.io/v1",
                "kind": "PartialObjectMetadata",
                "metadata": {"name": "pod-1", "namespace": "default"},
            },
            {
                "apiVersion": "meta.k8s.io/v1",
                "kind": "PartialObjectMetadata",
                "metadata": {"name": "pod-2", "namespace": "default"},
            },
        ],
    }
).encode()

PARTIAL_META_NODE_JSON = json.dumps(
    {
        "apiVersion": "meta.k8s.io/v1",
        "kind": "PartialObjectMetadata",
        "metadata": {"name": "my-node"},
    }
).encode()


@pytest.mark.anyio
async def test_metadata_get_builds_correct_request() -> None:
    client = StubClient(response_content=PARTIAL_META_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    result = await api.metadata.get("my-pod")
    req = client.last_request
    assert req.method == "GET"
    assert "/pods/my-pod" in req.url
    assert "namespaces/default" in req.url
    assert isinstance(result, PartialObjectMetadata)
    assert result.metadata.name == "my-pod"


@pytest.mark.anyio
async def test_metadata_get_with_explicit_namespace() -> None:
    client = StubClient(response_content=PARTIAL_META_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    await api.metadata.get("my-pod", namespace="other")
    req = client.last_request
    assert "namespaces/other" in req.url


@pytest.mark.anyio
async def test_metadata_get_ellipsis_uses_api_default_namespace() -> None:
    client = StubClient(response_content=PARTIAL_META_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="my-ns")
    await api.metadata.get("my-pod")
    req = client.last_request
    assert "namespaces/my-ns" in req.url


@pytest.mark.anyio
async def test_metadata_get_requires_namespace_for_namespaced_resource() -> None:
    client = StubClient(response_content=PARTIAL_META_JSON)
    api: Api[Pod] = Api(Pod, client=client)
    with pytest.raises(ValueError, match="Namespace is required"):
        await api.metadata.get("my-pod")


@pytest.mark.anyio
async def test_metadata_get_cluster_scoped_resource() -> None:
    client = StubClient(response_content=PARTIAL_META_NODE_JSON)
    api: Api[Node] = Api(Node, client=client)
    result = await api.metadata.get("my-node")
    req = client.last_request
    assert req.method == "GET"
    assert "/nodes/my-node" in req.url
    assert "namespaces" not in req.url
    assert isinstance(result, PartialObjectMetadata)
    assert result.metadata.name == "my-node"


@pytest.mark.anyio
async def test_metadata_get_cluster_scoped_rejects_namespace() -> None:
    client = StubClient(response_content=PARTIAL_META_NODE_JSON)
    api: Api[Node] = Api(Node, client=client)
    with pytest.raises(
        ValueError, match="Namespace is not supported for cluster-scoped resources"
    ):
        await api.metadata.get("my-node", namespace="some-ns")


@pytest.mark.anyio
async def test_metadata_get_with_resource_version() -> None:
    client = StubClient(response_content=PARTIAL_META_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    await api.metadata.get("my-pod", resource_version="42")
    req = client.last_request
    assert req.query_params is not None
    assert req.query_params.get("resourceVersion") == "42"


@pytest.mark.anyio
async def test_metadata_get_sets_accept_header() -> None:
    client = StubClient(response_content=PARTIAL_META_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    await api.metadata.get("my-pod")
    req = client.last_request
    assert req.headers is not None
    accept = req.headers.get("accept")
    assert accept is not None
    assert "PartialObjectMetadata" in accept


@pytest.mark.anyio
async def test_metadata_get_with_request_timeout() -> None:
    client = StubClient(response_content=PARTIAL_META_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    await api.metadata.get("my-pod", request_timeout=30)
    req = client.last_request
    assert isinstance(req.timeout, Timeout)
    assert req.timeout.total == 30


@pytest.mark.anyio
async def test_metadata_list_builds_correct_request() -> None:
    client = StubClient(response_content=PARTIAL_META_LIST_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    result = await api.metadata.list()
    req = client.last_request
    assert req.method == "GET"
    assert "/pods" in req.url
    assert "namespaces/default" in req.url
    assert len(result.items) == 2
    assert all(isinstance(item, PartialObjectMetadata) for item in result.items)
    assert result.items[0].metadata.name == "pod-1"
    assert result.items[1].metadata.name == "pod-2"


@pytest.mark.anyio
async def test_metadata_list_with_explicit_namespace() -> None:
    client = StubClient(response_content=PARTIAL_META_LIST_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    await api.metadata.list(namespace="other")
    req = client.last_request
    assert "namespaces/other" in req.url


@pytest.mark.anyio
async def test_metadata_list_without_namespace_lists_all() -> None:
    client = StubClient(response_content=PARTIAL_META_LIST_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    await api.metadata.list(namespace=None)
    req = client.last_request
    assert "namespaces" not in req.url


@pytest.mark.anyio
async def test_metadata_list_cluster_scoped_resource() -> None:
    node_list_json = json.dumps(
        {
            "apiVersion": "meta.k8s.io/v1",
            "kind": "PartialObjectMetadataList",
            "metadata": {"resourceVersion": "100"},
            "items": [
                {
                    "apiVersion": "meta.k8s.io/v1",
                    "kind": "PartialObjectMetadata",
                    "metadata": {"name": "node-1"},
                },
            ],
        }
    ).encode()
    client = StubClient(response_content=node_list_json)
    api: Api[Node] = Api(Node, client=client)
    result = await api.metadata.list()
    req = client.last_request
    assert req.method == "GET"
    assert "/nodes" in req.url
    assert "namespaces" not in req.url
    assert len(result.items) == 1


@pytest.mark.anyio
async def test_metadata_list_cluster_scoped_rejects_namespace() -> None:
    client = StubClient(response_content=PARTIAL_META_LIST_JSON)
    api: Api[Node] = Api(Node, client=client)
    with pytest.raises(
        ValueError, match="Namespace is not supported for cluster-scoped resources"
    ):
        await api.metadata.list(namespace="some-ns")


@pytest.mark.anyio
async def test_metadata_list_with_label_selector() -> None:
    client = StubClient(response_content=PARTIAL_META_LIST_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    await api.metadata.list(label_selector="app=web")
    req = client.last_request
    assert req.query_params is not None
    assert req.query_params.get("labelSelector") == "app=web"


@pytest.mark.anyio
async def test_metadata_list_with_field_selector() -> None:
    client = StubClient(response_content=PARTIAL_META_LIST_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    await api.metadata.list(field_selector="status.phase=Running")
    req = client.last_request
    assert req.query_params is not None
    assert req.query_params.get("fieldSelector") == "status.phase=Running"


@pytest.mark.anyio
async def test_metadata_list_with_limit_and_continue() -> None:
    client = StubClient(response_content=PARTIAL_META_LIST_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    await api.metadata.list(limit=10, continue_token="abc123")
    req = client.last_request
    assert req.query_params is not None
    assert req.query_params.get("limit") == "10"
    assert req.query_params.get("continue") == "abc123"


@pytest.mark.anyio
async def test_metadata_list_with_request_timeout() -> None:
    client = StubClient(response_content=PARTIAL_META_LIST_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    await api.metadata.list(request_timeout=60)
    req = client.last_request
    assert isinstance(req.timeout, Timeout)
    assert req.timeout.total == 60


@pytest.mark.anyio
async def test_metadata_list_sets_accept_header() -> None:
    client = StubClient(response_content=PARTIAL_META_LIST_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    await api.metadata.list()
    req = client.last_request
    assert req.headers is not None
    accept = req.headers.get("accept")
    assert accept is not None
    assert "PartialObjectMetadataList" in accept


@pytest.mark.anyio
async def test_metadata_patch_builds_correct_request() -> None:
    client = StubClient(response_content=PARTIAL_META_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    patch = MergePatch(
        PartialObjectMetadata.model_validate({"metadata": {"labels": {"env": "prod"}}})
    )
    result = await api.metadata.patch("my-pod", patch)
    req = client.last_request
    assert req.method == "PATCH"
    assert "/pods/my-pod" in req.url
    assert "namespaces/default" in req.url
    assert req.body is not None
    assert req.headers is not None
    assert req.headers.get("content-type") == "application/merge-patch+json"
    assert isinstance(result, PartialObjectMetadata)


@pytest.mark.anyio
async def test_metadata_patch_with_explicit_namespace() -> None:
    client = StubClient(response_content=PARTIAL_META_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    patch = MergePatch(
        PartialObjectMetadata.model_validate({"metadata": {"labels": {"env": "prod"}}})
    )
    await api.metadata.patch("my-pod", patch, namespace="other")
    req = client.last_request
    assert "namespaces/other" in req.url


@pytest.mark.anyio
async def test_metadata_patch_requires_namespace_for_namespaced_resource() -> None:
    client = StubClient(response_content=PARTIAL_META_JSON)
    api: Api[Pod] = Api(Pod, client=client)
    patch = MergePatch(
        PartialObjectMetadata.model_validate({"metadata": {"labels": {"env": "prod"}}})
    )
    with pytest.raises(ValueError, match="Namespace is required"):
        await api.metadata.patch("my-pod", patch)


@pytest.mark.anyio
async def test_metadata_patch_cluster_scoped_resource() -> None:
    client = StubClient(response_content=PARTIAL_META_NODE_JSON)
    api: Api[Node] = Api(Node, client=client)
    patch = MergePatch(
        PartialObjectMetadata.model_validate({"metadata": {"labels": {"env": "prod"}}})
    )
    result = await api.metadata.patch("my-node", patch)
    req = client.last_request
    assert req.method == "PATCH"
    assert "/nodes/my-node" in req.url
    assert "namespaces" not in req.url
    assert isinstance(result, PartialObjectMetadata)


@pytest.mark.anyio
async def test_metadata_patch_with_strategic_merge_patch() -> None:
    client = StubClient(response_content=PARTIAL_META_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    patch = StrategicMergePatch(
        PartialObjectMetadata.model_validate({"metadata": {"labels": {"env": "prod"}}})
    )
    await api.metadata.patch("my-pod", patch)
    req = client.last_request
    assert req.headers is not None
    assert req.headers.get("content-type") == "application/strategic-merge-patch+json"


@pytest.mark.anyio
async def test_metadata_patch_with_options() -> None:
    client = StubClient(response_content=PARTIAL_META_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    patch = MergePatch(
        PartialObjectMetadata.model_validate({"metadata": {"labels": {"env": "prod"}}})
    )
    await api.metadata.patch(
        "my-pod",
        patch,
        dry_run=True,
        field_manager="test-mgr",
        force=True,
        field_validation=FieldValidation.STRICT,
    )
    req = client.last_request
    assert req.query_params is not None
    assert req.query_params.get("dryRun") == "All"
    assert req.query_params.get("fieldManager") == "test-mgr"
    assert req.query_params.get("force") == "true"
    assert req.query_params.get("fieldValidation") == "Strict"


@pytest.mark.anyio
async def test_metadata_patch_with_request_timeout() -> None:
    client = StubClient(response_content=PARTIAL_META_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    patch = MergePatch(
        PartialObjectMetadata.model_validate({"metadata": {"labels": {"env": "prod"}}})
    )
    await api.metadata.patch("my-pod", patch, request_timeout=15)
    req = client.last_request
    assert isinstance(req.timeout, Timeout)
    assert req.timeout.total == 15


@pytest.mark.anyio
async def test_metadata_patch_sets_accept_header() -> None:
    client = StubClient(response_content=PARTIAL_META_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    patch = MergePatch(
        PartialObjectMetadata.model_validate({"metadata": {"labels": {"env": "prod"}}})
    )
    await api.metadata.patch("my-pod", patch)
    req = client.last_request
    assert req.headers is not None
    accept = req.headers.get("accept")
    assert accept is not None
    assert "PartialObjectMetadata" in accept


@pytest.mark.anyio
async def test_metadata_watch_yields_events() -> None:
    event_data = json.dumps(
        {
            "type": "ADDED",
            "object": {
                "apiVersion": "meta.k8s.io/v1",
                "kind": "PartialObjectMetadata",
                "metadata": {"name": "my-pod", "namespace": "default"},
            },
        }
    )
    client = StubClient(stream_lines=[event_data])
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    events: list[WatchEvent[PartialObjectMetadata]] = []
    async for event in api.metadata.watch():
        events.append(event)
    assert len(events) == 1
    assert events[0].type == EventType.ADDED
    assert isinstance(events[0].object, PartialObjectMetadata)
    assert events[0].object.metadata.name == "my-pod"


@pytest.mark.anyio
async def test_metadata_watch_builds_correct_request() -> None:
    client = StubClient(stream_lines=[])
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    async for _ in api.metadata.watch():
        pass
    req = client.last_request
    assert req.method == "GET"
    assert "/pods" in req.url
    assert "namespaces/default" in req.url
    assert req.query_params is not None
    assert req.query_params.get("watch") == "true"


@pytest.mark.anyio
async def test_metadata_watch_with_options() -> None:
    client = StubClient(stream_lines=[])
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    async for _ in api.metadata.watch(
        label_selector="app=web",
        field_selector="status.phase=Running",
        allow_bookmarks=True,
        send_initial_events=True,
        timeout_seconds=300,
        resource_version="42",
    ):
        pass
    req = client.last_request
    assert req.query_params is not None
    assert req.query_params.get("labelSelector") == "app=web"
    assert req.query_params.get("fieldSelector") == "status.phase=Running"
    assert req.query_params.get("allowBookmarks") == "true"
    assert req.query_params.get("sendInitialEvents") == "true"
    assert req.query_params.get("timeoutSeconds") == "300"
    assert req.query_params.get("resourceVersion") == "42"


@pytest.mark.anyio
async def test_metadata_watch_without_namespace_watches_all() -> None:
    client = StubClient(stream_lines=[])
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    async for _ in api.metadata.watch(namespace=None):
        pass
    req = client.last_request
    assert "namespaces" not in req.url


@pytest.mark.anyio
async def test_metadata_watch_cluster_scoped() -> None:
    client = StubClient(stream_lines=[])
    api: Api[Node] = Api(Node, client=client)
    async for _ in api.metadata.watch():
        pass
    req = client.last_request
    assert "/nodes" in req.url
    assert "namespaces" not in req.url


@pytest.mark.anyio
async def test_metadata_watch_sets_content_type_header() -> None:
    client = StubClient(stream_lines=[])
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    async for _ in api.metadata.watch():
        pass
    req = client.last_request
    assert req.headers is not None
    content_type = req.headers.get("content-type")
    assert content_type is not None
    assert "PartialObjectMetadata" in content_type


@pytest.mark.anyio
async def test_metadata_watch_with_request_timeout() -> None:
    client = StubClient(stream_lines=[])
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    async for _ in api.metadata.watch(request_timeout=120):
        pass
    req = client.last_request
    assert isinstance(req.timeout, Timeout)
    assert req.timeout.total == 120


@pytest.mark.anyio
async def test_metadata_is_always_available() -> None:
    client = StubClient(response_content=PARTIAL_META_JSON)
    pod_api: Api[Pod] = Api(Pod, client=client, namespace="default")
    node_api: Api[Node] = Api(Node, client=client)
    from kubex.api._metadata import MetadataAccessor

    assert isinstance(pod_api.metadata, MetadataAccessor)
    assert isinstance(node_api.metadata, MetadataAccessor)
