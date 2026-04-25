from __future__ import annotations

import json

import pytest

from kubex.core.params import (
    FieldValidation,
    PatchOptions,
    PostOptions,
    Timeout,
)
from kubex.core.patch import JsonPatch, MergePatch, StrategicMergePatch
from kubex.core.request_builder.builder import RequestBuilder
from pydantic import BaseModel


class _Stub(BaseModel):
    replicas: int = 3


_PATCH_HEADERS_CASES = [
    pytest.param(
        JsonPatch().add("/status/phase", "Running"),
        "application/json-patch+json",
        id="json_patch",
    ),
    pytest.param(MergePatch(_Stub()), "application/merge-patch+json", id="merge_patch"),
    pytest.param(
        StrategicMergePatch(_Stub()),
        "application/strategic-merge-patch+json",
        id="strategic_merge_patch",
    ),
]

_TIMEOUT_OBJECT = Timeout(total=60, connect=5)

_TIMEOUT_CASES = [
    pytest.param(..., ..., id="default_ellipsis"),
    pytest.param(15, Timeout(total=15), id="passthrough"),
    pytest.param(None, None, id="none"),
    pytest.param(_TIMEOUT_OBJECT, _TIMEOUT_OBJECT, id="object"),
]

_TIMEOUT_CASES_SHORT = [
    pytest.param(..., ..., id="default_ellipsis"),
    pytest.param(20, Timeout(total=20), id="passthrough"),
]


def _assert_timeout(actual: object, expected: object) -> None:
    if expected is ...:
        assert actual is Ellipsis
    elif expected is None:
        assert actual is None
    else:
        assert actual == expected


def test_get_subresource_method(ns_builder: RequestBuilder) -> None:
    req = ns_builder.get_subresource("status", "my-pod", "default")
    assert req.method == "GET"


def test_get_subresource_url_namespaced(ns_builder: RequestBuilder) -> None:
    req = ns_builder.get_subresource("status", "my-pod", "default")
    assert req.url == "/api/v1/namespaces/default/pods/my-pod/status"


def test_get_subresource_url_cluster_scoped(
    cluster_builder: RequestBuilder,
) -> None:
    req = cluster_builder.get_subresource("status", "my-node", None)
    assert req.url == "/api/v1/nodes/my-node/status"


def test_get_subresource_url_scale(ns_builder: RequestBuilder) -> None:
    req = ns_builder.get_subresource("scale", "my-pod", "default")
    assert req.url == "/api/v1/namespaces/default/pods/my-pod/scale"


def test_get_subresource_no_body(ns_builder: RequestBuilder) -> None:
    req = ns_builder.get_subresource("status", "my-pod", "default")
    assert req.body is None


def test_get_subresource_no_query_params(ns_builder: RequestBuilder) -> None:
    req = ns_builder.get_subresource("status", "my-pod", "default")
    assert req.query_params is None


def test_get_subresource_no_headers(ns_builder: RequestBuilder) -> None:
    req = ns_builder.get_subresource("status", "my-pod", "default")
    assert req.headers is None


@pytest.mark.parametrize("request_timeout,expected", _TIMEOUT_CASES)
def test_get_subresource_timeout(
    ns_builder: RequestBuilder, request_timeout: object, expected: object
) -> None:
    kwargs = {} if request_timeout is ... else {"request_timeout": request_timeout}
    req = ns_builder.get_subresource("status", "my-pod", "default", **kwargs)  # type: ignore[arg-type]
    _assert_timeout(req.timeout, expected)


def test_replace_subresource_method(ns_builder: RequestBuilder) -> None:
    req = ns_builder.replace_subresource(
        "status", "my-pod", "default", data="{}", options=PostOptions()
    )
    assert req.method == "PUT"


def test_replace_subresource_url_namespaced(
    ns_builder: RequestBuilder,
) -> None:
    req = ns_builder.replace_subresource(
        "status", "my-pod", "default", data="{}", options=PostOptions()
    )
    assert req.url == "/api/v1/namespaces/default/pods/my-pod/status"


def test_replace_subresource_url_cluster_scoped(
    cluster_builder: RequestBuilder,
) -> None:
    req = cluster_builder.replace_subresource(
        "status", "my-node", None, data="{}", options=PostOptions()
    )
    assert req.url == "/api/v1/nodes/my-node/status"


def test_replace_subresource_body_passthrough(
    ns_builder: RequestBuilder,
) -> None:
    body = '{"status":{"phase":"Running"}}'
    req = ns_builder.replace_subresource(
        "status", "my-pod", "default", data=body, options=PostOptions()
    )
    assert req.body == body


def test_replace_subresource_body_bytes(ns_builder: RequestBuilder) -> None:
    body = b'{"status":{"phase":"Running"}}'
    req = ns_builder.replace_subresource(
        "status", "my-pod", "default", data=body, options=PostOptions()
    )
    assert req.body == body


def test_replace_subresource_query_params_default(
    ns_builder: RequestBuilder,
) -> None:
    req = ns_builder.replace_subresource(
        "status", "my-pod", "default", data="{}", options=PostOptions()
    )
    assert req.query_params is None


def test_replace_subresource_query_params_dry_run(
    ns_builder: RequestBuilder,
) -> None:
    opts = PostOptions(dry_run=True, field_manager="mgr")
    req = ns_builder.replace_subresource(
        "status", "my-pod", "default", data="{}", options=opts
    )
    assert req.query_params == {"dryRun": "All", "fieldManager": "mgr"}


@pytest.mark.parametrize("request_timeout,expected", _TIMEOUT_CASES_SHORT)
def test_replace_subresource_timeout(
    ns_builder: RequestBuilder, request_timeout: object, expected: object
) -> None:
    kwargs = {} if request_timeout is ... else {"request_timeout": request_timeout}
    req = ns_builder.replace_subresource(
        "status",
        "my-pod",
        "default",
        data="{}",
        options=PostOptions(),
        **kwargs,  # type: ignore[arg-type]
    )
    _assert_timeout(req.timeout, expected)


def test_patch_subresource_method(ns_builder: RequestBuilder) -> None:
    patch = JsonPatch().add("/status/phase", "Running")
    req = ns_builder.patch_subresource(
        "status", "my-pod", "default", PatchOptions(), patch
    )
    assert req.method == "PATCH"


def test_patch_subresource_url_namespaced(ns_builder: RequestBuilder) -> None:
    patch = JsonPatch().add("/status/phase", "Running")
    req = ns_builder.patch_subresource(
        "status", "my-pod", "default", PatchOptions(), patch
    )
    assert req.url == "/api/v1/namespaces/default/pods/my-pod/status"


def test_patch_subresource_url_cluster_scoped(
    cluster_builder: RequestBuilder,
) -> None:
    patch = JsonPatch().add("/status/phase", "Running")
    req = cluster_builder.patch_subresource(
        "status", "my-node", None, PatchOptions(), patch
    )
    assert req.url == "/api/v1/nodes/my-node/status"


def test_patch_subresource_url_scale(ns_builder: RequestBuilder) -> None:
    patch = JsonPatch().add("/spec/replicas", 3)
    req = ns_builder.patch_subresource(
        "scale", "my-pod", "default", PatchOptions(), patch
    )
    assert req.url == "/api/v1/namespaces/default/pods/my-pod/scale"


def test_patch_subresource_body_json_patch(ns_builder: RequestBuilder) -> None:
    patch = JsonPatch().add("/status/phase", "Running")
    req = ns_builder.patch_subresource(
        "status", "my-pod", "default", PatchOptions(), patch
    )
    assert req.body is not None
    body = json.loads(req.body)
    assert body == [{"op": "add", "path": "/status/phase", "value": "Running"}]


@pytest.mark.parametrize("patch,expected_content_type", _PATCH_HEADERS_CASES)
def test_patch_subresource_headers(
    ns_builder: RequestBuilder, patch: object, expected_content_type: str
) -> None:
    req = ns_builder.patch_subresource(
        "status",
        "my-pod",
        "default",
        PatchOptions(),
        patch,  # type: ignore[arg-type]
    )
    assert req.headers == {
        "accept": "application/json",
        "content-type": expected_content_type,
    }


def test_patch_subresource_query_params_default(
    ns_builder: RequestBuilder,
) -> None:
    patch = JsonPatch().add("/x", 1)
    req = ns_builder.patch_subresource(
        "status", "my-pod", "default", PatchOptions(), patch
    )
    assert req.query_params is None


def test_patch_subresource_query_params_force(
    ns_builder: RequestBuilder,
) -> None:
    patch = JsonPatch().add("/x", 1)
    req = ns_builder.patch_subresource(
        "status", "my-pod", "default", PatchOptions(force=True), patch
    )
    assert req.query_params is not None
    assert req.query_params["force"] == "true"


def test_patch_subresource_query_params_field_validation(
    ns_builder: RequestBuilder,
) -> None:
    patch = JsonPatch().add("/x", 1)
    opts = PatchOptions(field_validation=FieldValidation.STRICT)
    req = ns_builder.patch_subresource("status", "my-pod", "default", opts, patch)
    assert req.query_params is not None
    assert req.query_params["fieldValidation"] == "Strict"


def test_patch_subresource_query_params_all(
    ns_builder: RequestBuilder,
) -> None:
    patch = JsonPatch().add("/x", 1)
    opts = PatchOptions(
        dry_run=True,
        field_manager="mgr",
        force=True,
        field_validation=FieldValidation.WARN,
    )
    req = ns_builder.patch_subresource("status", "my-pod", "default", opts, patch)
    assert req.query_params == {
        "dryRun": "All",
        "fieldManager": "mgr",
        "force": "true",
        "fieldValidation": "Warn",
    }


@pytest.mark.parametrize("request_timeout,expected", _TIMEOUT_CASES_SHORT)
def test_patch_subresource_timeout(
    ns_builder: RequestBuilder, request_timeout: object, expected: object
) -> None:
    patch = JsonPatch().add("/x", 1)
    kwargs = {} if request_timeout is ... else {"request_timeout": request_timeout}
    req = ns_builder.patch_subresource(
        "status",
        "my-pod",
        "default",
        PatchOptions(),
        patch,
        **kwargs,  # type: ignore[arg-type]
    )
    _assert_timeout(req.timeout, expected)
