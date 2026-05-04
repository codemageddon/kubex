from __future__ import annotations

import pytest

from kubex.core.params import (
    FieldValidation,
    GetOptions,
    ListOptions,
    PatchOptions,
    Timeout,
    WatchOptions,
)
from kubex.core.patch import ApplyPatch, JsonPatch, MergePatch, StrategicMergePatch
from kubex.core.request_builder.builder import RequestBuilder
from kubex.core.request_builder.constants import (
    ACCEPT_HEADER,
    APPLICATION_JSON_MIME_TYPE,
    CONTENT_TYPE_HEADER,
    METADATA_LIST_MIME_TYPE,
    METADATA_MIME_TYPE,
)
from pydantic import BaseModel


class _Stub(BaseModel):
    replicas: int = 3


_PATCH_CONTENT_TYPE_CASES = [
    pytest.param(
        JsonPatch().add("/metadata/labels/new", "value"),
        "application/json-patch+json",
        id="json_patch",
    ),
    pytest.param(MergePatch(_Stub()), "application/merge-patch+json", id="merge_patch"),
    pytest.param(
        StrategicMergePatch(_Stub()),
        "application/strategic-merge-patch+json",
        id="strategic_merge_patch",
    ),
    pytest.param(ApplyPatch(_Stub()), "application/apply-patch+yaml", id="apply_patch"),
]

_TIMEOUT_OBJECT = Timeout(total=60, connect=5)

_TIMEOUT_CASES = [
    pytest.param(..., ..., id="default_ellipsis"),
    pytest.param(30, Timeout(total=30), id="passthrough"),
    pytest.param(None, None, id="none"),
    pytest.param(_TIMEOUT_OBJECT, _TIMEOUT_OBJECT, id="object"),
]

_TIMEOUT_CASES_SHORT = [
    pytest.param(..., ..., id="default_ellipsis"),
    pytest.param(15, Timeout(total=15), id="passthrough"),
]


def _assert_timeout(actual: object, expected: object) -> None:
    if expected is ...:
        assert actual is Ellipsis
    elif expected is None:
        assert actual is None
    else:
        assert actual == expected


def test_get_metadata_method(ns_builder: RequestBuilder) -> None:
    req = ns_builder.get_metadata("my-pod", "default", GetOptions())
    assert req.method == "GET"


def test_get_metadata_url_namespaced(ns_builder: RequestBuilder) -> None:
    req = ns_builder.get_metadata("my-pod", "default", GetOptions())
    assert req.url == "/api/v1/namespaces/default/pods/my-pod"


def test_get_metadata_url_cluster_scoped(cluster_builder: RequestBuilder) -> None:
    req = cluster_builder.get_metadata("my-node", None, GetOptions())
    assert req.url == "/api/v1/nodes/my-node"


def test_get_metadata_accept_header(ns_builder: RequestBuilder) -> None:
    req = ns_builder.get_metadata("my-pod", "default", GetOptions())
    assert req.headers is not None
    assert req.headers[ACCEPT_HEADER] == METADATA_MIME_TYPE


def test_get_metadata_content_type_header(ns_builder: RequestBuilder) -> None:
    req = ns_builder.get_metadata("my-pod", "default", GetOptions())
    assert req.headers is not None
    assert req.headers[CONTENT_TYPE_HEADER] == APPLICATION_JSON_MIME_TYPE


def test_get_metadata_query_params_default(ns_builder: RequestBuilder) -> None:
    req = ns_builder.get_metadata("my-pod", "default", GetOptions())
    assert req.query_params is None


def test_get_metadata_query_params_resource_version(
    ns_builder: RequestBuilder,
) -> None:
    req = ns_builder.get_metadata(
        "my-pod", "default", GetOptions(resource_version="12345")
    )
    assert req.query_params == {"resourceVersion": "12345"}


@pytest.mark.parametrize("request_timeout,expected", _TIMEOUT_CASES)
def test_get_metadata_timeout(
    ns_builder: RequestBuilder, request_timeout: object, expected: object
) -> None:
    kwargs = {} if request_timeout is ... else {"request_timeout": request_timeout}
    req = ns_builder.get_metadata("my-pod", "default", GetOptions(), **kwargs)  # type: ignore[arg-type]
    _assert_timeout(req.timeout, expected)


def test_list_metadata_method(ns_builder: RequestBuilder) -> None:
    req = ns_builder.list_metadata("default", ListOptions())
    assert req.method == "GET"


def test_list_metadata_url_namespaced(ns_builder: RequestBuilder) -> None:
    req = ns_builder.list_metadata("default", ListOptions())
    assert req.url == "/api/v1/namespaces/default/pods"


def test_list_metadata_url_all_namespaces(ns_builder: RequestBuilder) -> None:
    req = ns_builder.list_metadata(None, ListOptions())
    assert req.url == "/api/v1/pods"


def test_list_metadata_url_cluster_scoped(cluster_builder: RequestBuilder) -> None:
    req = cluster_builder.list_metadata(None, ListOptions())
    assert req.url == "/api/v1/nodes"


def test_list_metadata_accept_header(ns_builder: RequestBuilder) -> None:
    req = ns_builder.list_metadata("default", ListOptions())
    assert req.headers is not None
    assert req.headers[ACCEPT_HEADER] == METADATA_LIST_MIME_TYPE


def test_list_metadata_content_type_header(ns_builder: RequestBuilder) -> None:
    req = ns_builder.list_metadata("default", ListOptions())
    assert req.headers is not None
    assert req.headers[CONTENT_TYPE_HEADER] == APPLICATION_JSON_MIME_TYPE


def test_list_metadata_query_params_default(ns_builder: RequestBuilder) -> None:
    req = ns_builder.list_metadata("default", ListOptions())
    assert req.query_params is None


def test_list_metadata_query_params_label_selector(
    ns_builder: RequestBuilder,
) -> None:
    req = ns_builder.list_metadata("default", ListOptions(label_selector="app=web"))
    assert req.query_params == {"labelSelector": "app=web"}


def test_list_metadata_query_params_all(ns_builder: RequestBuilder) -> None:
    opts = ListOptions(
        label_selector="app=web",
        field_selector="status.phase=Running",
        timeout_seconds=30,
        limit=50,
        continue_token="tok",
        resource_version="999",
    )
    req = ns_builder.list_metadata("default", opts)
    assert req.query_params == {
        "labelSelector": "app=web",
        "fieldSelector": "status.phase=Running",
        "timeoutSeconds": "30",
        "limit": "50",
        "continue": "tok",
        "resourceVersion": "999",
    }


@pytest.mark.parametrize("request_timeout,expected", _TIMEOUT_CASES_SHORT)
def test_list_metadata_timeout(
    ns_builder: RequestBuilder, request_timeout: object, expected: object
) -> None:
    kwargs = {} if request_timeout is ... else {"request_timeout": request_timeout}
    req = ns_builder.list_metadata("default", ListOptions(), **kwargs)  # type: ignore[arg-type]
    _assert_timeout(req.timeout, expected)


def test_watch_metadata_method(ns_builder: RequestBuilder) -> None:
    req = ns_builder.watch_metadata("default", WatchOptions())
    assert req.method == "GET"


def test_watch_metadata_url_namespaced(ns_builder: RequestBuilder) -> None:
    req = ns_builder.watch_metadata("default", WatchOptions())
    assert req.url == "/api/v1/namespaces/default/pods"


def test_watch_metadata_url_all_namespaces(ns_builder: RequestBuilder) -> None:
    req = ns_builder.watch_metadata(None, WatchOptions())
    assert req.url == "/api/v1/pods"


def test_watch_metadata_url_cluster_scoped(cluster_builder: RequestBuilder) -> None:
    req = cluster_builder.watch_metadata(None, WatchOptions())
    assert req.url == "/api/v1/nodes"


def test_watch_metadata_accept_header(ns_builder: RequestBuilder) -> None:
    req = ns_builder.watch_metadata("default", WatchOptions())
    assert req.headers is not None
    assert req.headers[ACCEPT_HEADER] == APPLICATION_JSON_MIME_TYPE


def test_watch_metadata_content_type_header(ns_builder: RequestBuilder) -> None:
    req = ns_builder.watch_metadata("default", WatchOptions())
    assert req.headers is not None
    assert req.headers[CONTENT_TYPE_HEADER] == METADATA_MIME_TYPE


def test_watch_metadata_query_params_from_options(
    ns_builder: RequestBuilder,
) -> None:
    opts = WatchOptions(
        label_selector="app=web",
        allow_bookmarks=True,
        send_initial_events=True,
        timeout_seconds=300,
    )
    req = ns_builder.watch_metadata("default", opts)
    assert req.query_params is not None
    assert req.query_params["labelSelector"] == "app=web"
    assert req.query_params["allowBookmarks"] == "true"
    assert req.query_params["sendInitialEvents"] == "true"
    assert req.query_params["timeoutSeconds"] == "300"


def test_watch_metadata_resource_version_injection(
    ns_builder: RequestBuilder,
) -> None:
    req = ns_builder.watch_metadata("default", WatchOptions(), resource_version="12345")
    assert req.query_params is not None
    assert req.query_params["resourceVersion"] == "12345"


def test_watch_metadata_resource_version_none_not_injected(
    ns_builder: RequestBuilder,
) -> None:
    req = ns_builder.watch_metadata("default", WatchOptions())
    assert req.query_params is not None
    assert "resourceVersion" not in req.query_params


@pytest.mark.parametrize("request_timeout,expected", _TIMEOUT_CASES_SHORT)
def test_watch_metadata_timeout(
    ns_builder: RequestBuilder, request_timeout: object, expected: object
) -> None:
    kwargs = {} if request_timeout is ... else {"request_timeout": request_timeout}
    req = ns_builder.watch_metadata("default", WatchOptions(), **kwargs)  # type: ignore[arg-type]
    _assert_timeout(req.timeout, expected)


def test_patch_metadata_method(ns_builder: RequestBuilder) -> None:
    patch = JsonPatch().add("/metadata/labels/new", "value")
    req = ns_builder.patch_metadata("my-pod", "default", PatchOptions(), patch)
    assert req.method == "PATCH"


def test_patch_metadata_url_namespaced(ns_builder: RequestBuilder) -> None:
    patch = JsonPatch().add("/metadata/labels/new", "value")
    req = ns_builder.patch_metadata("my-pod", "default", PatchOptions(), patch)
    assert req.url == "/api/v1/namespaces/default/pods/my-pod"


def test_patch_metadata_url_cluster_scoped(cluster_builder: RequestBuilder) -> None:
    patch = JsonPatch().add("/metadata/labels/new", "value")
    req = cluster_builder.patch_metadata("my-node", None, PatchOptions(), patch)
    assert req.url == "/api/v1/nodes/my-node"


def test_patch_metadata_accept_header(ns_builder: RequestBuilder) -> None:
    patch = JsonPatch().add("/metadata/labels/new", "value")
    req = ns_builder.patch_metadata("my-pod", "default", PatchOptions(), patch)
    assert req.headers is not None
    assert req.headers[ACCEPT_HEADER] == METADATA_MIME_TYPE


@pytest.mark.parametrize("patch,expected_content_type", _PATCH_CONTENT_TYPE_CASES)
def test_patch_metadata_content_type(
    ns_builder: RequestBuilder, patch: object, expected_content_type: str
) -> None:
    req = ns_builder.patch_metadata("my-pod", "default", PatchOptions(), patch)  # type: ignore[arg-type]
    assert req.headers is not None
    assert req.headers[CONTENT_TYPE_HEADER] == expected_content_type


def test_patch_metadata_body(ns_builder: RequestBuilder) -> None:
    patch = JsonPatch().add("/metadata/labels/app", "web")
    req = ns_builder.patch_metadata("my-pod", "default", PatchOptions(), patch)
    assert req.body is not None
    import json

    body = json.loads(req.body)
    assert body == [{"op": "add", "path": "/metadata/labels/app", "value": "web"}]


def test_patch_metadata_query_params_default(ns_builder: RequestBuilder) -> None:
    patch = JsonPatch().add("/x", 1)
    req = ns_builder.patch_metadata("my-pod", "default", PatchOptions(), patch)
    assert req.query_params is None


def test_patch_metadata_query_params_force(ns_builder: RequestBuilder) -> None:
    patch = JsonPatch().add("/x", 1)
    req = ns_builder.patch_metadata(
        "my-pod", "default", PatchOptions(force=True), patch
    )
    assert req.query_params is not None
    assert req.query_params["force"] == "true"


def test_patch_metadata_query_params_field_validation(
    ns_builder: RequestBuilder,
) -> None:
    patch = JsonPatch().add("/x", 1)
    opts = PatchOptions(field_validation=FieldValidation.STRICT)
    req = ns_builder.patch_metadata("my-pod", "default", opts, patch)
    assert req.query_params is not None
    assert req.query_params["fieldValidation"] == "Strict"


def test_patch_metadata_query_params_all(ns_builder: RequestBuilder) -> None:
    patch = JsonPatch().add("/x", 1)
    opts = PatchOptions(
        dry_run=True,
        field_manager="mgr",
        force=True,
        field_validation=FieldValidation.WARN,
    )
    req = ns_builder.patch_metadata("my-pod", "default", opts, patch)
    assert req.query_params == {
        "dryRun": "All",
        "fieldManager": "mgr",
        "force": "true",
        "fieldValidation": "Warn",
    }


@pytest.mark.parametrize("request_timeout,expected", _TIMEOUT_CASES_SHORT)
def test_patch_metadata_timeout(
    ns_builder: RequestBuilder, request_timeout: object, expected: object
) -> None:
    patch = JsonPatch().add("/x", 1)
    kwargs = {} if request_timeout is ... else {"request_timeout": request_timeout}
    req = ns_builder.patch_metadata(
        "my-pod",
        "default",
        PatchOptions(),
        patch,
        **kwargs,  # type: ignore[arg-type]
    )
    _assert_timeout(req.timeout, expected)
