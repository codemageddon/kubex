from __future__ import annotations

import pytest

from kubex.api import Api
from kubex.core.params import FieldValidation
from kubex.core.patch import MergePatch
from kubex.k8s.v1_35.core.v1.pod import Pod

from .conftest import StubClient

POD_JSON = b'{"apiVersion": "v1", "kind": "Pod", "metadata": {"name": "my-pod", "namespace": "default"}}'


@pytest.mark.anyio
async def test_resize_get_builds_correct_request() -> None:
    client = StubClient(response_content=POD_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    result = await api.resize.get("my-pod")
    req = client.last_request
    assert req.method == "GET"
    assert req.url.endswith("/pods/my-pod/resize")
    assert "namespaces/default" in req.url
    assert isinstance(result, Pod)
    assert result.metadata is not None
    assert result.metadata.name == "my-pod"


@pytest.mark.anyio
async def test_resize_get_with_explicit_namespace() -> None:
    client = StubClient(response_content=POD_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    await api.resize.get("my-pod", namespace="other")
    req = client.last_request
    assert "namespaces/other" in req.url


@pytest.mark.anyio
async def test_resize_replace_builds_correct_request() -> None:
    client = StubClient(response_content=POD_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    pod = Pod.model_validate(
        {"apiVersion": "v1", "kind": "Pod", "metadata": {"name": "my-pod"}}
    )
    result = await api.resize.replace("my-pod", pod)
    req = client.last_request
    assert req.method == "PUT"
    assert req.url.endswith("/pods/my-pod/resize")
    assert "namespaces/default" in req.url
    assert req.body is not None
    assert isinstance(result, Pod)


@pytest.mark.anyio
async def test_resize_replace_with_dry_run() -> None:
    client = StubClient(response_content=POD_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    pod = Pod.model_validate(
        {"apiVersion": "v1", "kind": "Pod", "metadata": {"name": "my-pod"}}
    )
    await api.resize.replace("my-pod", pod, dry_run=True)
    req = client.last_request
    assert req.query_params is not None
    assert req.query_params.get("dryRun") == "All"


@pytest.mark.anyio
async def test_resize_replace_with_field_manager() -> None:
    client = StubClient(response_content=POD_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    pod = Pod.model_validate(
        {"apiVersion": "v1", "kind": "Pod", "metadata": {"name": "my-pod"}}
    )
    await api.resize.replace("my-pod", pod, field_manager="my-manager")
    req = client.last_request
    assert req.query_params is not None
    assert req.query_params.get("fieldManager") == "my-manager"


@pytest.mark.anyio
async def test_resize_patch_builds_correct_request() -> None:
    client = StubClient(response_content=POD_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    patch = MergePatch(Pod.model_validate({"metadata": {"labels": {"a": "b"}}}))
    result = await api.resize.patch("my-pod", patch)
    req = client.last_request
    assert req.method == "PATCH"
    assert req.url.endswith("/pods/my-pod/resize")
    assert "namespaces/default" in req.url
    assert req.body is not None
    assert req.headers is not None
    assert req.headers.get("content-type") == "application/merge-patch+json"
    assert isinstance(result, Pod)


@pytest.mark.anyio
async def test_resize_patch_with_options() -> None:
    client = StubClient(response_content=POD_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    patch = MergePatch(Pod.model_validate({"metadata": {"labels": {"a": "b"}}}))
    await api.resize.patch(
        "my-pod",
        patch,
        dry_run=True,
        field_manager="mgr",
        force=True,
        field_validation=FieldValidation.STRICT,
    )
    req = client.last_request
    assert req.query_params is not None
    assert req.query_params.get("dryRun") == "All"
    assert req.query_params.get("fieldManager") == "mgr"
    assert req.query_params.get("force") == "true"
    assert req.query_params.get("fieldValidation") == "Strict"


@pytest.mark.anyio
async def test_resize_get_requires_namespace() -> None:
    client = StubClient(response_content=POD_JSON)
    api: Api[Pod] = Api(Pod, client=client)
    with pytest.raises(ValueError, match="Namespace is required"):
        await api.resize.get("my-pod")


@pytest.mark.anyio
async def test_resize_replace_requires_namespace() -> None:
    client = StubClient(response_content=POD_JSON)
    api: Api[Pod] = Api(Pod, client=client)
    pod = Pod.model_validate(
        {"apiVersion": "v1", "kind": "Pod", "metadata": {"name": "my-pod"}}
    )
    with pytest.raises(ValueError, match="Namespace is required"):
        await api.resize.replace("my-pod", pod)


@pytest.mark.anyio
async def test_resize_patch_requires_namespace() -> None:
    client = StubClient(response_content=POD_JSON)
    api: Api[Pod] = Api(Pod, client=client)
    patch = MergePatch(Pod.model_validate({"metadata": {"labels": {"a": "b"}}}))
    with pytest.raises(ValueError, match="Namespace is required"):
        await api.resize.patch("my-pod", patch)


@pytest.mark.anyio
async def test_resize_get_deserializes_response() -> None:
    response_json = (
        b'{"apiVersion": "v1", "kind": "Pod",'
        b' "metadata": {"name": "my-pod", "namespace": "default"},'
        b' "status": {"phase": "Running"}}'
    )
    client = StubClient(response_content=response_json)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    result = await api.resize.get("my-pod")
    assert isinstance(result, Pod)
    assert result.status is not None
    assert result.status.phase == "Running"
