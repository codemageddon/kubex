from __future__ import annotations

import pytest

from kubex.api import Api
from kubex.core.params import FieldValidation
from kubex.core.patch import MergePatch
from kubex.k8s.v1_35.core.v1.pod import Pod

from .conftest import StubClient

POD_JSON = b'{"apiVersion": "v1", "kind": "Pod", "metadata": {"name": "my-pod", "namespace": "default"}}'
POD_WITH_STATUS_JSON = (
    b'{"apiVersion": "v1", "kind": "Pod",'
    b' "metadata": {"name": "my-pod", "namespace": "default"},'
    b' "status": {"phase": "Running"}}'
)

_ACCESSOR_CASES = [
    pytest.param("status", "/pods/my-pod/status", id="status"),
    pytest.param("resize", "/pods/my-pod/resize", id="resize"),
    pytest.param(
        "ephemeral_containers",
        "/pods/my-pod/ephemeralcontainers",
        id="ephemeral_containers",
    ),
]


@pytest.mark.parametrize("attr_name,url_suffix", _ACCESSOR_CASES)
@pytest.mark.anyio
async def test_get_builds_correct_request(attr_name: str, url_suffix: str) -> None:
    client = StubClient(response_content=POD_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    result = await getattr(api, attr_name).get("my-pod")
    req = client.last_request
    assert req.method == "GET"
    assert req.url.endswith(url_suffix)
    assert "namespaces/default" in req.url
    assert isinstance(result, Pod)
    assert result.metadata is not None
    assert result.metadata.name == "my-pod"


@pytest.mark.parametrize("attr_name,url_suffix", _ACCESSOR_CASES)
@pytest.mark.anyio
async def test_get_with_explicit_namespace(attr_name: str, url_suffix: str) -> None:
    client = StubClient(response_content=POD_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    await getattr(api, attr_name).get("my-pod", namespace="other")
    req = client.last_request
    assert "namespaces/other" in req.url


@pytest.mark.parametrize("attr_name,url_suffix", _ACCESSOR_CASES)
@pytest.mark.anyio
async def test_replace_builds_correct_request(attr_name: str, url_suffix: str) -> None:
    client = StubClient(response_content=POD_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    pod = Pod.model_validate(
        {"apiVersion": "v1", "kind": "Pod", "metadata": {"name": "my-pod"}}
    )
    result = await getattr(api, attr_name).replace("my-pod", pod)
    req = client.last_request
    assert req.method == "PUT"
    assert req.url.endswith(url_suffix)
    assert "namespaces/default" in req.url
    assert req.body is not None
    assert isinstance(result, Pod)


@pytest.mark.parametrize("attr_name,url_suffix", _ACCESSOR_CASES)
@pytest.mark.anyio
async def test_replace_with_dry_run(attr_name: str, url_suffix: str) -> None:
    client = StubClient(response_content=POD_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    pod = Pod.model_validate(
        {"apiVersion": "v1", "kind": "Pod", "metadata": {"name": "my-pod"}}
    )
    await getattr(api, attr_name).replace("my-pod", pod, dry_run=True)
    req = client.last_request
    assert req.query_params is not None
    assert req.query_params.get("dryRun") == "All"


@pytest.mark.parametrize("attr_name,url_suffix", _ACCESSOR_CASES)
@pytest.mark.anyio
async def test_replace_with_field_manager(attr_name: str, url_suffix: str) -> None:
    client = StubClient(response_content=POD_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    pod = Pod.model_validate(
        {"apiVersion": "v1", "kind": "Pod", "metadata": {"name": "my-pod"}}
    )
    await getattr(api, attr_name).replace("my-pod", pod, field_manager="my-manager")
    req = client.last_request
    assert req.query_params is not None
    assert req.query_params.get("fieldManager") == "my-manager"


@pytest.mark.parametrize("attr_name,url_suffix", _ACCESSOR_CASES)
@pytest.mark.anyio
async def test_patch_builds_correct_request(attr_name: str, url_suffix: str) -> None:
    client = StubClient(response_content=POD_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    patch = MergePatch(Pod.model_validate({"metadata": {"labels": {"a": "b"}}}))
    result = await getattr(api, attr_name).patch("my-pod", patch)
    req = client.last_request
    assert req.method == "PATCH"
    assert req.url.endswith(url_suffix)
    assert "namespaces/default" in req.url
    assert req.body is not None
    assert req.headers is not None
    assert req.headers.get("content-type") == "application/merge-patch+json"
    assert isinstance(result, Pod)


@pytest.mark.parametrize("attr_name,url_suffix", _ACCESSOR_CASES)
@pytest.mark.anyio
async def test_patch_with_options(attr_name: str, url_suffix: str) -> None:
    client = StubClient(response_content=POD_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    patch = MergePatch(Pod.model_validate({"metadata": {"labels": {"a": "b"}}}))
    await getattr(api, attr_name).patch(
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


@pytest.mark.parametrize("attr_name,url_suffix", _ACCESSOR_CASES)
@pytest.mark.anyio
async def test_get_requires_namespace(attr_name: str, url_suffix: str) -> None:
    client = StubClient(response_content=POD_JSON)
    api: Api[Pod] = Api(Pod, client=client)
    with pytest.raises(ValueError, match="Namespace is required"):
        await getattr(api, attr_name).get("my-pod")


@pytest.mark.parametrize("attr_name,url_suffix", _ACCESSOR_CASES)
@pytest.mark.anyio
async def test_replace_requires_namespace(attr_name: str, url_suffix: str) -> None:
    client = StubClient(response_content=POD_JSON)
    api: Api[Pod] = Api(Pod, client=client)
    pod = Pod.model_validate(
        {"apiVersion": "v1", "kind": "Pod", "metadata": {"name": "my-pod"}}
    )
    with pytest.raises(ValueError, match="Namespace is required"):
        await getattr(api, attr_name).replace("my-pod", pod)


@pytest.mark.parametrize("attr_name,url_suffix", _ACCESSOR_CASES)
@pytest.mark.anyio
async def test_patch_requires_namespace(attr_name: str, url_suffix: str) -> None:
    client = StubClient(response_content=POD_JSON)
    api: Api[Pod] = Api(Pod, client=client)
    patch = MergePatch(Pod.model_validate({"metadata": {"labels": {"a": "b"}}}))
    with pytest.raises(ValueError, match="Namespace is required"):
        await getattr(api, attr_name).patch("my-pod", patch)


@pytest.mark.parametrize("attr_name,url_suffix", _ACCESSOR_CASES)
@pytest.mark.anyio
async def test_get_deserializes_response(attr_name: str, url_suffix: str) -> None:
    client = StubClient(response_content=POD_WITH_STATUS_JSON)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    result = await getattr(api, attr_name).get("my-pod")
    assert isinstance(result, Pod)
    assert result.status is not None
    assert result.status.phase == "Running"
