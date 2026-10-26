"""Api-level checks that invalid names never reach the wire and that options
are forwarded in the shape the apiserver expects."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

import pytest

from kubex.api import Api
from kubex.configuration import ClientConfiguration
from kubex.core.patch import ApplyPatch, JsonPatch
from kubex.k8s.v1_35.core.v1.config_map import ConfigMap
from kubex.k8s.v1_35.core.v1.namespace import Namespace
from kubex.k8s.v1_35.core.v1.pod import Pod
from kubex_core.models.metadata import ObjectMetadata
from kubex_core.models.partial_object_meta import PartialObjectMetadata
from test.stub_client import StubClient


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


_POD_JSON = json.dumps(
    {"apiVersion": "v1", "kind": "Pod", "metadata": {"name": "p", "namespace": "ns"}}
).encode()

_META_JSON = json.dumps(
    {
        "apiVersion": "meta.k8s.io/v1",
        "kind": "PartialObjectMetadata",
        "metadata": {"name": "p", "namespace": "ns"},
    }
).encode()


_SingleObjectCall = Callable[[Api[Pod], Any], Awaitable[Any]]

_SINGLE_OBJECT_CALLS: list[Any] = [
    pytest.param(lambda api, name: api.get(name), id="get"),
    pytest.param(lambda api, name: api.delete(name), id="delete"),
    pytest.param(lambda api, name: api.patch(name, JsonPatch()), id="patch"),
    pytest.param(
        lambda api, name: api.replace(name, Pod(metadata=ObjectMetadata())),
        id="replace",
    ),
    pytest.param(lambda api, name: api.metadata.get(name), id="metadata.get"),
    pytest.param(
        lambda api, name: api.metadata.patch(name, JsonPatch()), id="metadata.patch"
    ),
    pytest.param(lambda api, name: api.status.get(name), id="status.get"),
    pytest.param(lambda api, name: api.logs.get(name), id="logs.get"),
    pytest.param(
        lambda api, name: api.ephemeral_containers.get(name),
        id="ephemeral_containers.get",
    ),
    pytest.param(lambda api, name: api.resize.get(name), id="resize.get"),
]


@pytest.mark.anyio
@pytest.mark.parametrize("call", _SINGLE_OBJECT_CALLS)
@pytest.mark.parametrize("name", [None, ""], ids=["none", "empty"])
async def test_empty_name_never_sends_a_request(
    call: _SingleObjectCall, name: str | None
) -> None:
    client = StubClient(response_content=_POD_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="ns")
    with pytest.raises(ValueError, match="^resource name may not be empty$"):
        await call(api, name)
    assert client.requests == []


@pytest.mark.anyio
async def test_delete_with_unset_generated_name_is_rejected() -> None:
    """The reviewer's repro: `delete(obj.metadata.name)` on an object created via
    generate_name without capturing the response used to wipe the collection."""
    client = StubClient(response_content=b'{"kind": "Status", "apiVersion": "v1"}')
    api: Api[ConfigMap] = Api(ConfigMap, client=client, namespace="ns")
    cm = ConfigMap(metadata=ObjectMetadata(generate_name="tmp-"))
    with pytest.raises(ValueError):
        await api.delete(cm.metadata.name)  # type: ignore[arg-type]
    assert client.requests == []


@pytest.mark.anyio
async def test_traversal_name_is_rejected() -> None:
    client = StubClient(response_content=_POD_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="a")
    with pytest.raises(ValueError, match="may not contain '/'"):
        await api.get("../../b/pods/x")
    assert client.requests == []


@pytest.mark.anyio
async def test_name_is_percent_encoded() -> None:
    client = StubClient(response_content=_POD_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="ns")
    await api.get("weird#name")
    assert client.last_request.url == "/api/v1/namespaces/ns/pods/weird%23name"


@pytest.mark.anyio
async def test_empty_explicit_namespace_is_rejected() -> None:
    client = StubClient(response_content=_POD_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="ns")
    with pytest.raises(ValueError, match="^namespace may not be empty$"):
        await api.get("p", namespace="")
    with pytest.raises(ValueError, match="^namespace may not be empty$"):
        await api.list(namespace="")
    assert client.requests == []


def test_empty_configured_namespace_means_unset() -> None:
    client = StubClient(
        ClientConfiguration(
            url="https://example.invalid", insecure_skip_tls_verify=True, namespace=""
        )
    )
    api: Api[Pod] = Api(Pod, client=client)
    assert api._namespace is None
    ns_api: Api[Namespace] = Api(Namespace, client=client)
    assert ns_api._namespace is None


@pytest.mark.anyio
async def test_dry_run_delete_body() -> None:
    client = StubClient(response_content=b'{"kind": "Status", "apiVersion": "v1"}')
    api: Api[Pod] = Api(Pod, client=client, namespace="ns")
    await api.delete("p", dry_run=True)
    assert client.last_request.body is not None
    assert json.loads(client.last_request.body) == {"dryRun": ["All"]}


@pytest.mark.anyio
async def test_patch_accepts_str_field_validation() -> None:
    client = StubClient(response_content=_POD_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="ns")
    await api.patch("p", JsonPatch(), field_validation="Strict")
    assert client.last_request.query_params == {"fieldValidation": "Strict"}


@pytest.mark.anyio
async def test_list_accepts_str_version_match() -> None:
    client = StubClient(
        response_content=b'{"apiVersion": "v1", "kind": "PodList", "metadata": {}, "items": []}'
    )
    api: Api[Pod] = Api(Pod, client=client, namespace="ns")
    await api.list(version_match="NotOlderThan", resource_version="0")
    assert client.last_request.query_params == {
        "resourceVersionMatch": "NotOlderThan",
        "resourceVersion": "0",
    }


@pytest.mark.anyio
async def test_metadata_apply_patch_uses_target_kind() -> None:
    client = StubClient(response_content=_META_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="ns")
    await api.metadata.patch(
        "p",
        ApplyPatch(PartialObjectMetadata(metadata=ObjectMetadata(labels={"a": "b"}))),
        field_manager="ctrl",
        force=True,
    )
    req = client.last_request
    assert isinstance(req.body, str)
    assert json.loads(req.body) == {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"labels": {"a": "b"}},
    }
    assert req.query_params == {"fieldManager": "ctrl", "force": "true"}


@pytest.mark.anyio
async def test_watch_send_initial_events_enables_bookmarks() -> None:
    client = StubClient()
    api: Api[Pod] = Api(Pod, client=client, namespace="ns")
    async for _ in api.watch(send_initial_events=True):
        pass
    assert client.last_request.query_params is not None
    assert client.last_request.query_params["allowWatchBookmarks"] == "true"


@pytest.mark.anyio
async def test_watch_send_initial_events_without_bookmarks_raises() -> None:
    client = StubClient()
    api: Api[Pod] = Api(Pod, client=client, namespace="ns")
    with pytest.raises(ValueError, match="allow_bookmarks"):
        async for _ in api.watch(send_initial_events=True, allow_bookmarks=False):
            pass
    assert client.requests == []


@pytest.mark.anyio
async def test_logs_since_time() -> None:
    client = StubClient(response_content=b"line\n")
    api: Api[Pod] = Api(Pod, client=client, namespace="ns")
    await api.logs.get(
        "p", since_time=datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    )
    assert client.last_request.query_params == {"sinceTime": "2026-01-02T03:04:05Z"}
    with pytest.raises(ValueError, match="mutually exclusive"):
        await api.logs.get("p", since_seconds=5, since_time=datetime.now(timezone.utc))
