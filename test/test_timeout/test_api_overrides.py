from __future__ import annotations

import json
from typing import Any

import pytest

from kubex.api import Api
from kubex.core.params import Timeout
from kubex.core.patch import MergePatch
from kubex.k8s.v1_35.apps.v1.deployment import Deployment
from kubex.k8s.v1_35.core.v1.pod import Pod

from .conftest import StubClient

_POD_RESPONSE = b'{"apiVersion": "v1", "kind": "Pod", "metadata": {"name": "x"}}'
_POD_OBJ = {"apiVersion": "v1", "kind": "Pod", "metadata": {"name": "x"}}

_TIMEOUT_INSTANCE = Timeout(connect=1, read=2)


def _pod_api(client: StubClient) -> Api[Pod]:
    return Api(Pod, client=client, namespace="default")


_GET_TIMEOUT_CASES = [
    pytest.param({}, Ellipsis, id="no_override_leaves_ellipsis"),
    pytest.param({"request_timeout": 2.5}, Timeout(total=2.5), id="float_sets_total"),
    pytest.param({"request_timeout": None}, None, id="none_disables"),
    pytest.param(
        {"request_timeout": _TIMEOUT_INSTANCE},
        _TIMEOUT_INSTANCE,
        id="instance_passthrough",
    ),
]


@pytest.mark.parametrize("kwargs,expected", _GET_TIMEOUT_CASES)
@pytest.mark.anyio
async def test_get_timeout_override(kwargs: dict[str, Any], expected: object) -> None:
    client = StubClient(response_content=_POD_RESPONSE)
    await _pod_api(client).get("x", **kwargs)
    actual = client.last_request.timeout
    if expected is Ellipsis:
        assert actual is Ellipsis
    elif expected is None:
        assert actual is None
    elif expected is _TIMEOUT_INSTANCE:
        assert actual is _TIMEOUT_INSTANCE
    else:
        assert actual == expected


@pytest.mark.anyio
async def test_list_override_flows_through_without_colliding_with_server_timeout() -> (
    None
):
    client = StubClient(
        response_content=(
            b'{"apiVersion": "v1", "kind": "PodList", "metadata": {}, "items": []}'
        )
    )
    await _pod_api(client).list(timeout=30, request_timeout=4.0)
    req = client.last_request
    assert req.timeout == Timeout(total=4.0)
    assert req.query_params is not None
    assert req.query_params.get("timeoutSeconds") == "30"


@pytest.mark.anyio
async def test_watch_override_flows_through() -> None:
    watch_line = json.dumps(
        {
            "type": "ADDED",
            "object": {
                "apiVersion": "v1",
                "kind": "Pod",
                "metadata": {"name": "x"},
            },
        }
    )
    client = StubClient(stream_lines=[watch_line])
    api = _pod_api(client)
    events = [event async for event in api.watch(request_timeout=7.5)]
    assert len(events) == 1
    assert client.last_request.timeout == Timeout(total=7.5)


@pytest.mark.anyio
async def test_create_override_flows_through() -> None:
    client = StubClient(response_content=_POD_RESPONSE)
    pod = Pod.model_validate(_POD_OBJ)
    await _pod_api(client).create(pod, request_timeout=1.0)
    assert client.last_request.timeout == Timeout(total=1.0)


@pytest.mark.anyio
async def test_delete_override_flows_through() -> None:
    client = StubClient(response_content=_POD_RESPONSE)
    await _pod_api(client).delete("x", request_timeout=2.0)
    assert client.last_request.timeout == Timeout(total=2.0)


@pytest.mark.anyio
async def test_patch_override_flows_through() -> None:
    client = StubClient(response_content=_POD_RESPONSE)
    patch = MergePatch(Pod.model_validate({"metadata": {"labels": {"a": "b"}}}))
    await _pod_api(client).patch("x", patch, request_timeout=3.0)
    assert client.last_request.timeout == Timeout(total=3.0)


@pytest.mark.anyio
async def test_logs_override_flows_through() -> None:
    client = StubClient(response_content=b"log-line\n")
    api = _pod_api(client)
    await api.logs.get("x", request_timeout=5.0)
    assert client.last_request.timeout == Timeout(total=5.0)


@pytest.mark.anyio
async def test_stream_logs_override_flows_through() -> None:
    client = StubClient(stream_lines=["hello"])
    api = _pod_api(client)
    lines = [line async for line in api.logs.stream("x", request_timeout=6.0)]
    assert lines == ["hello"]
    assert client.last_request.timeout == Timeout(total=6.0)


_METADATA_OVERRIDE_CASES = [
    pytest.param(
        "list",
        (
            b'{"apiVersion": "meta.k8s.io/v1", "kind": "PartialObjectMetadataList",'
            b' "metadata": {}, "items": []}'
        ),
        {},
        8.0,
        id="list_metadata",
    ),
    pytest.param(
        "get",
        (
            b'{"apiVersion": "meta.k8s.io/v1", "kind": "PartialObjectMetadata",'
            b' "metadata": {"name": "x"}}'
        ),
        {"name": "x"},
        9.0,
        id="get_metadata",
    ),
]


@pytest.mark.parametrize(
    "method,response,extra_args,timeout_val", _METADATA_OVERRIDE_CASES
)
@pytest.mark.anyio
async def test_metadata_override_flows_through(
    method: str,
    response: bytes,
    extra_args: dict[str, str],
    timeout_val: float,
) -> None:
    client = StubClient(response_content=response)
    api = _pod_api(client)
    accessor = api.metadata
    if method == "get":
        await accessor.get(extra_args["name"], request_timeout=timeout_val)
    else:
        await accessor.list(request_timeout=timeout_val)
    assert client.last_request.timeout == Timeout(total=timeout_val)


def _deploy_api(client: StubClient) -> Api[Deployment]:
    return Api(Deployment, client=client, namespace="default")


@pytest.mark.anyio
async def test_get_scale_override_flows_through() -> None:
    client = StubClient(
        response_content=(
            b'{"apiVersion": "autoscaling/v1", "kind": "Scale",'
            b' "metadata": {"name": "x"}, "spec": {"replicas": 1}}'
        )
    )
    await _deploy_api(client).scale.get("x", request_timeout=10.0)
    assert client.last_request.timeout == Timeout(total=10.0)
