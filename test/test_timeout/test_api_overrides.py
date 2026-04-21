from __future__ import annotations

import json
from typing import Any, Type

import pytest

from kubex.api import Api
from kubex.api._subressource import ScaleMixin
from kubex.core.params import NamespaceTypes, Timeout
from kubex.core.patch import MergePatch
from kubex.core.request_builder.builder import RequestBuilder
from kubex.k8s.v1_35.apps.v1.deployment import Deployment
from kubex.k8s.v1_35.core.v1.pod import Pod

from .conftest import StubClient


class _ScaleOnly(ScaleMixin[Deployment]):
    """Minimal ScaleMixin host used only for timeout-flow testing.

    Avoids the ``_check_implemented`` name collision between ``LogsMixin`` and
    ``ScaleMixin`` that would otherwise bite us if we composed with ``Api``.
    """

    def __init__(self, client: StubClient) -> None:
        self._resource: Type[Deployment] = Deployment
        self._client = client
        self._request_builder = RequestBuilder(
            resource_config=Deployment.__RESOURCE_CONFIG__,
        )
        self._namespace: NamespaceTypes = "default"

    def _ensure_required_namespace(self, namespace: Any) -> NamespaceTypes:
        return "default"

    def _ensure_optional_namespace(self, namespace: Any) -> NamespaceTypes:
        return "default"


def _pod_api(client: StubClient) -> Api[Pod]:
    return Api(Pod, client=client, namespace="default")


@pytest.mark.anyio
async def test_get_no_override_leaves_request_timeout_as_ellipsis() -> None:
    client = StubClient(
        response_content=b'{"apiVersion": "v1", "kind": "Pod", "metadata": {"name": "x"}}'
    )
    await _pod_api(client).get("x")
    assert client.last_request.timeout is Ellipsis


@pytest.mark.anyio
async def test_get_float_override_sets_total() -> None:
    client = StubClient(
        response_content=b'{"apiVersion": "v1", "kind": "Pod", "metadata": {"name": "x"}}'
    )
    await _pod_api(client).get("x", request_timeout=2.5)
    assert client.last_request.timeout == Timeout(total=2.5)


@pytest.mark.anyio
async def test_get_none_override_disables_timeout() -> None:
    client = StubClient(
        response_content=b'{"apiVersion": "v1", "kind": "Pod", "metadata": {"name": "x"}}'
    )
    await _pod_api(client).get("x", request_timeout=None)
    assert client.last_request.timeout is None


@pytest.mark.anyio
async def test_get_timeout_instance_passthrough() -> None:
    timeout = Timeout(connect=1, read=2)
    client = StubClient(
        response_content=b'{"apiVersion": "v1", "kind": "Pod", "metadata": {"name": "x"}}'
    )
    await _pod_api(client).get("x", request_timeout=timeout)
    assert client.last_request.timeout is timeout


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
    # Server-side Kubernetes timeout remains on the query string
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
    client = StubClient(
        response_content=b'{"apiVersion": "v1", "kind": "Pod", "metadata": {"name": "x"}}'
    )
    pod = Pod.model_validate(
        {"apiVersion": "v1", "kind": "Pod", "metadata": {"name": "x"}}
    )
    await _pod_api(client).create(pod, request_timeout=1.0)
    assert client.last_request.timeout == Timeout(total=1.0)


@pytest.mark.anyio
async def test_delete_override_flows_through() -> None:
    client = StubClient(
        response_content=b'{"apiVersion": "v1", "kind": "Pod", "metadata": {"name": "x"}}'
    )
    await _pod_api(client).delete("x", request_timeout=2.0)
    assert client.last_request.timeout == Timeout(total=2.0)


@pytest.mark.anyio
async def test_patch_override_flows_through() -> None:
    client = StubClient(
        response_content=b'{"apiVersion": "v1", "kind": "Pod", "metadata": {"name": "x"}}'
    )
    patch = MergePatch(Pod.model_validate({"metadata": {"labels": {"a": "b"}}}))
    await _pod_api(client).patch("x", patch, request_timeout=3.0)
    assert client.last_request.timeout == Timeout(total=3.0)


@pytest.mark.anyio
async def test_logs_override_flows_through() -> None:
    client = StubClient(response_content=b"log-line\n")
    api = _pod_api(client)
    await api.logs("x", request_timeout=5.0)
    assert client.last_request.timeout == Timeout(total=5.0)


@pytest.mark.anyio
async def test_stream_logs_override_flows_through() -> None:
    client = StubClient(stream_lines=["hello"])
    api = _pod_api(client)
    lines = [line async for line in api.stream_logs("x", request_timeout=6.0)]
    assert lines == ["hello"]
    assert client.last_request.timeout == Timeout(total=6.0)


@pytest.mark.anyio
async def test_list_metadata_override_flows_through() -> None:
    client = StubClient(
        response_content=(
            b'{"apiVersion": "meta.k8s.io/v1", "kind": "PartialObjectMetadataList",'
            b' "metadata": {}, "items": []}'
        )
    )
    await _pod_api(client).list_metadata(request_timeout=8.0)
    assert client.last_request.timeout == Timeout(total=8.0)


@pytest.mark.anyio
async def test_get_metadata_override_flows_through() -> None:
    client = StubClient(
        response_content=(
            b'{"apiVersion": "meta.k8s.io/v1", "kind": "PartialObjectMetadata",'
            b' "metadata": {"name": "x"}}'
        )
    )
    await _pod_api(client).get_metadata("x", request_timeout=9.0)
    assert client.last_request.timeout == Timeout(total=9.0)


@pytest.mark.anyio
async def test_get_scale_override_flows_through() -> None:
    client = StubClient(
        response_content=(
            b'{"apiVersion": "autoscaling/v1", "kind": "Scale",'
            b' "metadata": {"name": "x"}, "spec": {"replicas": 1}}'
        )
    )
    await _ScaleOnly(client).get_scale("x", request_timeout=10.0)
    assert client.last_request.timeout == Timeout(total=10.0)
