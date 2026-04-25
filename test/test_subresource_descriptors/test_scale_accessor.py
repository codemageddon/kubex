from __future__ import annotations

import json

import pytest

from kubex.api import Api
from kubex.core.params import FieldValidation
from kubex.core.patch import MergePatch
from kubex.k8s.v1_35.apps.v1.deployment import Deployment
from kubex_core.models.scale import Scale

from .conftest import StubClient

SCALE_JSON = json.dumps(
    {
        "apiVersion": "autoscaling/v1",
        "kind": "Scale",
        "metadata": {"name": "my-deploy", "namespace": "default"},
        "spec": {"replicas": 3},
    }
).encode()


@pytest.mark.anyio
async def test_scale_get_builds_correct_request() -> None:
    client = StubClient(response_content=SCALE_JSON)
    api: Api[Deployment] = Api(Deployment, client=client, namespace="default")
    result = await api.scale.get("my-deploy")
    req = client.last_request
    assert req.method == "GET"
    assert req.url.endswith("/deployments/my-deploy/scale")
    assert "namespaces/default" in req.url
    assert isinstance(result, Scale)
    assert result.spec.replicas == 3


@pytest.mark.anyio
async def test_scale_get_with_explicit_namespace() -> None:
    client = StubClient(response_content=SCALE_JSON)
    api: Api[Deployment] = Api(Deployment, client=client, namespace="default")
    await api.scale.get("my-deploy", namespace="other")
    req = client.last_request
    assert "namespaces/other" in req.url


@pytest.mark.anyio
async def test_scale_replace_builds_correct_request() -> None:
    client = StubClient(response_content=SCALE_JSON)
    api: Api[Deployment] = Api(Deployment, client=client, namespace="default")
    scale = Scale.model_validate(
        {
            "apiVersion": "autoscaling/v1",
            "kind": "Scale",
            "metadata": {"name": "my-deploy"},
            "spec": {"replicas": 5},
        }
    )
    result = await api.scale.replace("my-deploy", scale)
    req = client.last_request
    assert req.method == "PUT"
    assert req.url.endswith("/deployments/my-deploy/scale")
    assert "namespaces/default" in req.url
    assert req.body is not None
    body = json.loads(req.body)
    assert body["spec"]["replicas"] == 5
    assert isinstance(result, Scale)


@pytest.mark.anyio
async def test_scale_replace_with_explicit_namespace() -> None:
    client = StubClient(response_content=SCALE_JSON)
    api: Api[Deployment] = Api(Deployment, client=client, namespace="default")
    scale = Scale.model_validate(
        {
            "apiVersion": "autoscaling/v1",
            "kind": "Scale",
            "metadata": {"name": "my-deploy"},
            "spec": {"replicas": 2},
        }
    )
    await api.scale.replace("my-deploy", scale, namespace="other")
    req = client.last_request
    assert "namespaces/other" in req.url


_REPLACE_OPTION_CASES = [
    pytest.param({"dry_run": True}, "dryRun", "All", id="dry_run"),
    pytest.param({"field_manager": "mgr"}, "fieldManager", "mgr", id="field_manager"),
]


@pytest.mark.parametrize("kwargs,param_key,param_value", _REPLACE_OPTION_CASES)
@pytest.mark.anyio
async def test_scale_replace_with_option(
    kwargs: dict[str, object], param_key: str, param_value: str
) -> None:
    client = StubClient(response_content=SCALE_JSON)
    api: Api[Deployment] = Api(Deployment, client=client, namespace="default")
    scale = Scale.model_validate(
        {
            "apiVersion": "autoscaling/v1",
            "kind": "Scale",
            "metadata": {"name": "my-deploy"},
            "spec": {"replicas": 1},
        }
    )
    await api.scale.replace("my-deploy", scale, **kwargs)  # type: ignore[arg-type]
    req = client.last_request
    assert req.query_params is not None
    assert req.query_params.get(param_key) == param_value


@pytest.mark.anyio
async def test_scale_replace_requires_namespace() -> None:
    client = StubClient(response_content=SCALE_JSON)
    api: Api[Deployment] = Api(Deployment, client=client)
    scale = Scale.model_validate(
        {
            "apiVersion": "autoscaling/v1",
            "kind": "Scale",
            "metadata": {"name": "my-deploy"},
            "spec": {"replicas": 1},
        }
    )
    with pytest.raises(ValueError, match="Namespace is required"):
        await api.scale.replace("my-deploy", scale)


@pytest.mark.anyio
async def test_scale_patch_builds_correct_request() -> None:
    client = StubClient(response_content=SCALE_JSON)
    api: Api[Deployment] = Api(Deployment, client=client, namespace="default")
    patch = MergePatch(Scale.model_validate({"metadata": {}, "spec": {"replicas": 10}}))
    result = await api.scale.patch("my-deploy", patch)
    req = client.last_request
    assert req.method == "PATCH"
    assert req.url.endswith("/deployments/my-deploy/scale")
    assert "namespaces/default" in req.url
    assert req.body is not None
    assert req.headers is not None
    assert req.headers.get("content-type") == "application/merge-patch+json"
    assert isinstance(result, Scale)


@pytest.mark.anyio
async def test_scale_patch_with_explicit_namespace() -> None:
    client = StubClient(response_content=SCALE_JSON)
    api: Api[Deployment] = Api(Deployment, client=client, namespace="default")
    patch = MergePatch(Scale.model_validate({"metadata": {}, "spec": {"replicas": 2}}))
    await api.scale.patch("my-deploy", patch, namespace="other")
    req = client.last_request
    assert "namespaces/other" in req.url


@pytest.mark.anyio
async def test_scale_patch_with_options() -> None:
    client = StubClient(response_content=SCALE_JSON)
    api: Api[Deployment] = Api(Deployment, client=client, namespace="default")
    patch = MergePatch(Scale.model_validate({"metadata": {}, "spec": {"replicas": 7}}))
    await api.scale.patch(
        "my-deploy",
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
async def test_scale_patch_requires_namespace() -> None:
    client = StubClient(response_content=SCALE_JSON)
    api: Api[Deployment] = Api(Deployment, client=client)
    patch = MergePatch(Scale.model_validate({"metadata": {}, "spec": {"replicas": 1}}))
    with pytest.raises(ValueError, match="Namespace is required"):
        await api.scale.patch("my-deploy", patch)


@pytest.mark.anyio
async def test_scale_get_deserializes_response() -> None:
    response = json.dumps(
        {
            "apiVersion": "autoscaling/v1",
            "kind": "Scale",
            "metadata": {"name": "my-deploy", "namespace": "default"},
            "spec": {"replicas": 42},
            "status": {"replicas": 42},
        }
    ).encode()
    client = StubClient(response_content=response)
    api: Api[Deployment] = Api(Deployment, client=client, namespace="default")
    result = await api.scale.get("my-deploy")
    assert isinstance(result, Scale)
    assert result.spec.replicas == 42
    assert result.status is not None
    assert result.status.replicas == 42
