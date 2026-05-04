from __future__ import annotations

import json

import pytest

from kubex.api import Api
from kubex.core.params import Timeout
from kubex.k8s.v1_35.core.v1.node import Node
from kubex.k8s.v1_35.core.v1.pod import Pod
from kubex_core.models.list_entity import ListEntity
from kubex_core.models.status import Status
from test.stub_client import StubClient


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


POD_JSON = json.dumps(
    {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"name": "my-pod", "namespace": "default"},
    }
).encode()

POD_LIST_JSON = json.dumps(
    {
        "apiVersion": "v1",
        "kind": "PodList",
        "metadata": {"resourceVersion": "100"},
        "items": [
            {
                "apiVersion": "v1",
                "kind": "Pod",
                "metadata": {"name": "pod-1", "namespace": "default"},
            },
            {
                "apiVersion": "v1",
                "kind": "Pod",
                "metadata": {"name": "pod-2", "namespace": "default"},
            },
        ],
    }
).encode()

STATUS_JSON = json.dumps(
    {
        "apiVersion": "v1",
        "kind": "Status",
        "metadata": {},
        "status": "Success",
        "code": 200,
    }
).encode()


@pytest.mark.anyio
async def test_replace_builds_correct_request() -> None:
    client = StubClient(response_content=POD_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    pod = Pod.model_validate(
        {"apiVersion": "v1", "kind": "Pod", "metadata": {"name": "my-pod"}}
    )
    result = await api.replace("my-pod", pod)
    req = client.last_request
    assert req.method == "PUT"
    assert "/pods/my-pod" in req.url
    assert "namespaces/default" in req.url
    assert req.body is not None
    assert isinstance(result, Pod)
    assert result.metadata is not None
    assert result.metadata.name == "my-pod"


@pytest.mark.anyio
async def test_replace_with_explicit_namespace() -> None:
    client = StubClient(response_content=POD_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    pod = Pod.model_validate(
        {"apiVersion": "v1", "kind": "Pod", "metadata": {"name": "my-pod"}}
    )
    await api.replace("my-pod", pod, namespace="other")
    req = client.last_request
    assert "namespaces/other" in req.url


@pytest.mark.anyio
async def test_replace_requires_namespace_for_namespaced_resource() -> None:
    client = StubClient(response_content=POD_JSON)
    api: Api[Pod] = Api(Pod, client=client)
    pod = Pod.model_validate(
        {"apiVersion": "v1", "kind": "Pod", "metadata": {"name": "my-pod"}}
    )
    with pytest.raises(ValueError, match="Namespace is required"):
        await api.replace("my-pod", pod)


@pytest.mark.anyio
async def test_replace_cluster_scoped() -> None:
    node_json = json.dumps(
        {"apiVersion": "v1", "kind": "Node", "metadata": {"name": "my-node"}}
    ).encode()
    client = StubClient(response_content=node_json)
    api: Api[Node] = Api(Node, client=client)
    node = Node.model_validate(
        {"apiVersion": "v1", "kind": "Node", "metadata": {"name": "my-node"}}
    )
    result = await api.replace("my-node", node)
    req = client.last_request
    assert req.method == "PUT"
    assert "/nodes/my-node" in req.url
    assert "namespaces" not in req.url
    assert isinstance(result, Node)


@pytest.mark.anyio
async def test_replace_serializes_body_as_camel_case() -> None:
    client = StubClient(response_content=POD_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    pod = Pod.model_validate(
        {"apiVersion": "v1", "kind": "Pod", "metadata": {"name": "my-pod"}}
    )
    await api.replace("my-pod", pod)
    req = client.last_request
    assert req.body is not None
    body = json.loads(req.body)
    assert "apiVersion" in body
    assert "api_version" not in body


_REPLACE_OPTION_CASES = [
    pytest.param({"dry_run": True}, "dryRun", "All", id="dry_run"),
    pytest.param({"field_manager": "mgr"}, "fieldManager", "mgr", id="field_manager"),
]


@pytest.mark.parametrize("kwargs,param_key,param_value", _REPLACE_OPTION_CASES)
@pytest.mark.anyio
async def test_replace_with_option(
    kwargs: dict[str, object], param_key: str, param_value: str
) -> None:
    client = StubClient(response_content=POD_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    pod = Pod.model_validate(
        {"apiVersion": "v1", "kind": "Pod", "metadata": {"name": "my-pod"}}
    )
    await api.replace("my-pod", pod, **kwargs)  # type: ignore[arg-type]
    req = client.last_request
    assert req.query_params is not None
    assert req.query_params.get(param_key) == param_value


@pytest.mark.anyio
async def test_replace_with_request_timeout() -> None:
    client = StubClient(response_content=POD_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    pod = Pod.model_validate(
        {"apiVersion": "v1", "kind": "Pod", "metadata": {"name": "my-pod"}}
    )
    await api.replace("my-pod", pod, request_timeout=15)
    req = client.last_request
    assert isinstance(req.timeout, Timeout)
    assert req.timeout.total == 15


@pytest.mark.anyio
async def test_delete_collection_returns_status() -> None:
    client = StubClient(response_content=STATUS_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    result = await api.delete_collection()
    req = client.last_request
    assert req.method == "DELETE"
    assert "/pods" in req.url
    assert "namespaces/default" in req.url
    assert isinstance(result, Status)
    assert result.status == "Success"


@pytest.mark.anyio
async def test_delete_collection_returns_list_on_non_status_response() -> None:
    client = StubClient(response_content=POD_LIST_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    result = await api.delete_collection()
    assert isinstance(result, ListEntity)
    assert len(result.items) == 2


@pytest.mark.anyio
async def test_delete_collection_with_explicit_namespace() -> None:
    client = StubClient(response_content=STATUS_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    await api.delete_collection(namespace="other")
    req = client.last_request
    assert "namespaces/other" in req.url


@pytest.mark.anyio
async def test_delete_collection_all_namespaces() -> None:
    client = StubClient(response_content=STATUS_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    await api.delete_collection(namespace=None)
    req = client.last_request
    assert "namespaces" not in req.url


@pytest.mark.anyio
async def test_delete_collection_cluster_scoped() -> None:
    client = StubClient(response_content=STATUS_JSON)
    api: Api[Node] = Api(Node, client=client)
    result = await api.delete_collection()
    req = client.last_request
    assert req.method == "DELETE"
    assert "/nodes" in req.url
    assert "namespaces" not in req.url
    assert isinstance(result, Status)


_LIST_OPTION_CASES = [
    pytest.param(
        {"label_selector": "app=old"}, "labelSelector", "app=old", id="label_selector"
    ),
    pytest.param(
        {"field_selector": "status.phase=Failed"},
        "fieldSelector",
        "status.phase=Failed",
        id="field_selector",
    ),
    pytest.param({"timeout_seconds": 30}, "timeoutSeconds", "30", id="timeout_seconds"),
    pytest.param({"limit": 50}, "limit", "50", id="limit"),
    pytest.param({"continue_token": "tok"}, "continue", "tok", id="continue_token"),
]


@pytest.mark.parametrize("kwargs,param_key,param_value", _LIST_OPTION_CASES)
@pytest.mark.anyio
async def test_delete_collection_list_option(
    kwargs: dict[str, object], param_key: str, param_value: str
) -> None:
    client = StubClient(response_content=STATUS_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    await api.delete_collection(**kwargs)  # type: ignore[arg-type]
    req = client.last_request
    assert req.query_params is not None
    assert req.query_params.get(param_key) == param_value


_DELETE_OPTION_CASES = [
    pytest.param({"dry_run": True}, "dryRun", "All", id="dry_run"),
    pytest.param(
        {"grace_period_seconds": 0}, "gracePeriodSeconds", 0, id="grace_period"
    ),
    pytest.param(
        {"propagation_policy": "Foreground"},
        "propagationPolicy",
        "Foreground",
        id="propagation_policy",
    ),
]


@pytest.mark.parametrize("kwargs,body_key,body_value", _DELETE_OPTION_CASES)
@pytest.mark.anyio
async def test_delete_collection_delete_option(
    kwargs: dict[str, object], body_key: str, body_value: object
) -> None:
    client = StubClient(response_content=STATUS_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    await api.delete_collection(**kwargs)  # type: ignore[arg-type]
    req = client.last_request
    assert req.body is not None
    body = json.loads(req.body)
    assert body[body_key] == body_value


@pytest.mark.anyio
async def test_delete_collection_with_request_timeout() -> None:
    client = StubClient(response_content=STATUS_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    await api.delete_collection(request_timeout=20)
    req = client.last_request
    assert isinstance(req.timeout, Timeout)
    assert req.timeout.total == 20
