from __future__ import annotations

import json


import pytest

from kubex.core.params import (
    DeleteOptions,
    DryRun,
    FieldValidation,
    GetOptions,
    ListOptions,
    PatchOptions,
    PostOptions,
    Precondition,
    PropagationPolicy,
    Timeout,
    VersionMatch,
    WatchOptions,
)
from kubex.core.patch import ApplyPatch, JsonPatch, MergePatch, StrategicMergePatch
from kubex.core.request_builder.builder import RequestBuilder
from pydantic import BaseModel


class _Stub(BaseModel):
    replicas: int = 3


_PATCH_HEADERS_CASES = [
    pytest.param(
        JsonPatch().add("/metadata/labels/app", "web"),
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
    pytest.param(30, Timeout(total=30), id="int_passthrough"),
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


def test_get_method(ns_builder: RequestBuilder) -> None:
    req = ns_builder.get("my-pod", "default", GetOptions())
    assert req.method == "GET"


def test_get_url_namespaced(ns_builder: RequestBuilder) -> None:
    req = ns_builder.get("my-pod", "default", GetOptions())
    assert req.url == "/api/v1/namespaces/default/pods/my-pod"


def test_get_url_cluster_scoped(cluster_builder: RequestBuilder) -> None:
    req = cluster_builder.get("my-node", None, GetOptions())
    assert req.url == "/api/v1/nodes/my-node"


def test_get_query_params_default(ns_builder: RequestBuilder) -> None:
    req = ns_builder.get("my-pod", "default", GetOptions())
    assert req.query_params is None


def test_get_query_params_resource_version(ns_builder: RequestBuilder) -> None:
    req = ns_builder.get("my-pod", "default", GetOptions(resource_version="12345"))
    assert req.query_params == {"resourceVersion": "12345"}


@pytest.mark.parametrize("request_timeout,expected", _TIMEOUT_CASES)
def test_get_timeout(
    ns_builder: RequestBuilder, request_timeout: object, expected: object
) -> None:
    kwargs = {} if request_timeout is ... else {"request_timeout": request_timeout}
    req = ns_builder.get("my-pod", "default", GetOptions(), **kwargs)  # type: ignore[arg-type]
    _assert_timeout(req.timeout, expected)


def test_list_method(ns_builder: RequestBuilder) -> None:
    req = ns_builder.list("default", ListOptions())
    assert req.method == "GET"


def test_list_url_namespaced(ns_builder: RequestBuilder) -> None:
    req = ns_builder.list("default", ListOptions())
    assert req.url == "/api/v1/namespaces/default/pods"


def test_list_url_all_namespaces(ns_builder: RequestBuilder) -> None:
    req = ns_builder.list(None, ListOptions())
    assert req.url == "/api/v1/pods"


def test_list_url_cluster_scoped(cluster_builder: RequestBuilder) -> None:
    req = cluster_builder.list(None, ListOptions())
    assert req.url == "/api/v1/nodes"


def test_list_query_params_default(ns_builder: RequestBuilder) -> None:
    req = ns_builder.list("default", ListOptions())
    assert req.query_params is None


def test_list_query_params_label_selector(ns_builder: RequestBuilder) -> None:
    req = ns_builder.list("default", ListOptions(label_selector="app=web"))
    assert req.query_params == {"labelSelector": "app=web"}


def test_list_query_params_field_selector(ns_builder: RequestBuilder) -> None:
    req = ns_builder.list("default", ListOptions(field_selector="status.phase=Running"))
    assert req.query_params == {"fieldSelector": "status.phase=Running"}


def test_list_query_params_limit(ns_builder: RequestBuilder) -> None:
    req = ns_builder.list("default", ListOptions(limit=100))
    assert req.query_params == {"limit": "100"}


def test_list_query_params_continue_token(ns_builder: RequestBuilder) -> None:
    req = ns_builder.list("default", ListOptions(continue_token="abc123"))
    assert req.query_params == {"continue": "abc123"}


def test_list_query_params_version_match(ns_builder: RequestBuilder) -> None:
    opts = ListOptions(version_match=VersionMatch.EXACT)
    req = ns_builder.list("default", opts)
    assert req.query_params == {"resourceVersionMatch": "Exact"}


def test_list_query_params_version_match_and_resource_version(
    ns_builder: RequestBuilder,
) -> None:
    opts = ListOptions(
        version_match=VersionMatch.NOT_EXACT,
        resource_version="100",
    )
    req = ns_builder.list("default", opts)
    assert req.query_params == {
        "resourceVersionMatch": "NotOlderThan",
        "resourceVersion": "100",
    }


def test_list_query_params_all(ns_builder: RequestBuilder) -> None:
    opts = ListOptions(
        label_selector="app=web",
        field_selector="status.phase=Running",
        timeout_seconds=30,
        limit=50,
        continue_token="tok",
        version_match=VersionMatch.EXACT,
        resource_version="999",
    )
    req = ns_builder.list("default", opts)
    assert req.query_params == {
        "labelSelector": "app=web",
        "fieldSelector": "status.phase=Running",
        "timeoutSeconds": "30",
        "limit": "50",
        "continue": "tok",
        "resourceVersionMatch": "Exact",
        "resourceVersion": "999",
    }


@pytest.mark.parametrize("request_timeout,expected", _TIMEOUT_CASES_SHORT)
def test_list_timeout(
    ns_builder: RequestBuilder, request_timeout: object, expected: object
) -> None:
    kwargs = {} if request_timeout is ... else {"request_timeout": request_timeout}
    req = ns_builder.list("default", ListOptions(), **kwargs)  # type: ignore[arg-type]
    _assert_timeout(req.timeout, expected)


def test_create_method(ns_builder: RequestBuilder) -> None:
    req = ns_builder.create("default", PostOptions(), data='{"kind":"Pod"}')
    assert req.method == "POST"


def test_create_url_namespaced(ns_builder: RequestBuilder) -> None:
    req = ns_builder.create("default", PostOptions(), data="{}")
    assert req.url == "/api/v1/namespaces/default/pods"


def test_create_url_cluster_scoped(cluster_builder: RequestBuilder) -> None:
    req = cluster_builder.create(None, PostOptions(), data="{}")
    assert req.url == "/api/v1/nodes"


def test_create_body_passthrough(ns_builder: RequestBuilder) -> None:
    body = '{"kind":"Pod","apiVersion":"v1"}'
    req = ns_builder.create("default", PostOptions(), data=body)
    assert req.body == body


def test_create_body_bytes(ns_builder: RequestBuilder) -> None:
    body = b'{"kind":"Pod"}'
    req = ns_builder.create("default", PostOptions(), data=body)
    assert req.body == body


def test_create_query_params_default(ns_builder: RequestBuilder) -> None:
    req = ns_builder.create("default", PostOptions(), data="{}")
    assert req.query_params is None


def test_create_query_params_dry_run(ns_builder: RequestBuilder) -> None:
    req = ns_builder.create("default", PostOptions(dry_run=True), data="{}")
    assert req.query_params == {"dryRun": "All"}


def test_create_query_params_field_manager(ns_builder: RequestBuilder) -> None:
    req = ns_builder.create("default", PostOptions(field_manager="test-mgr"), data="{}")
    assert req.query_params == {"fieldManager": "test-mgr"}


def test_create_query_params_dry_run_and_field_manager(
    ns_builder: RequestBuilder,
) -> None:
    opts = PostOptions(dry_run=DryRun.ALL, field_manager="mgr")
    req = ns_builder.create("default", opts, data="{}")
    assert req.query_params == {"dryRun": "All", "fieldManager": "mgr"}


@pytest.mark.parametrize("request_timeout,expected", _TIMEOUT_CASES_SHORT)
def test_create_timeout(
    ns_builder: RequestBuilder, request_timeout: object, expected: object
) -> None:
    kwargs = {} if request_timeout is ... else {"request_timeout": request_timeout}
    req = ns_builder.create("default", PostOptions(), data="{}", **kwargs)  # type: ignore[arg-type]
    _assert_timeout(req.timeout, expected)


def test_delete_method(ns_builder: RequestBuilder) -> None:
    req = ns_builder.delete("my-pod", "default", DeleteOptions())
    assert req.method == "DELETE"


def test_delete_url_namespaced(ns_builder: RequestBuilder) -> None:
    req = ns_builder.delete("my-pod", "default", DeleteOptions())
    assert req.url == "/api/v1/namespaces/default/pods/my-pod"


def test_delete_url_cluster_scoped(cluster_builder: RequestBuilder) -> None:
    req = cluster_builder.delete("my-node", None, DeleteOptions())
    assert req.url == "/api/v1/nodes/my-node"


def test_delete_body_default_is_none(ns_builder: RequestBuilder) -> None:
    req = ns_builder.delete("my-pod", "default", DeleteOptions())
    assert req.body is None


def test_delete_body_grace_period(ns_builder: RequestBuilder) -> None:
    opts = DeleteOptions(grace_period_seconds=30)
    req = ns_builder.delete("my-pod", "default", opts)
    assert req.body is not None
    body = json.loads(req.body)
    assert body == {"gracePeriodSeconds": 30}


def test_delete_body_propagation_policy(ns_builder: RequestBuilder) -> None:
    opts = DeleteOptions(propagation_policy=PropagationPolicy.FOREGROUND)
    req = ns_builder.delete("my-pod", "default", opts)
    assert req.body is not None
    body = json.loads(req.body)
    assert body == {"propagationPolicy": "Foreground"}


def test_delete_body_propagation_policy_string(ns_builder: RequestBuilder) -> None:
    opts = DeleteOptions(propagation_policy="Background")
    req = ns_builder.delete("my-pod", "default", opts)
    assert req.body is not None
    body = json.loads(req.body)
    assert body == {"propagationPolicy": "Background"}


def test_delete_body_preconditions_uid(ns_builder: RequestBuilder) -> None:
    opts = DeleteOptions(preconditions=Precondition(uid="abc-123"))
    req = ns_builder.delete("my-pod", "default", opts)
    assert req.body is not None
    body = json.loads(req.body)
    assert body == {"preconditions": {"uid": "abc-123"}}


def test_delete_body_preconditions_resource_version(
    ns_builder: RequestBuilder,
) -> None:
    opts = DeleteOptions(preconditions=Precondition(resource_version="999"))
    req = ns_builder.delete("my-pod", "default", opts)
    assert req.body is not None
    body = json.loads(req.body)
    assert body == {"preconditions": {"resourceVersion": "999"}}


def test_delete_body_preconditions_uid_and_resource_version(
    ns_builder: RequestBuilder,
) -> None:
    opts = DeleteOptions(
        preconditions=Precondition(uid="abc-123", resource_version="999")
    )
    req = ns_builder.delete("my-pod", "default", opts)
    assert req.body is not None
    body = json.loads(req.body)
    assert body == {"preconditions": {"uid": "abc-123", "resourceVersion": "999"}}


def test_delete_body_dry_run(ns_builder: RequestBuilder) -> None:
    opts = DeleteOptions(dry_run=True)
    req = ns_builder.delete("my-pod", "default", opts)
    assert req.body is not None
    body = json.loads(req.body)
    assert body == {"dryRun": "All"}


@pytest.mark.parametrize("request_timeout,expected", _TIMEOUT_CASES_SHORT)
def test_delete_timeout(
    ns_builder: RequestBuilder, request_timeout: object, expected: object
) -> None:
    kwargs = {} if request_timeout is ... else {"request_timeout": request_timeout}
    req = ns_builder.delete("my-pod", "default", DeleteOptions(), **kwargs)  # type: ignore[arg-type]
    _assert_timeout(req.timeout, expected)


def test_delete_collection_method(ns_builder: RequestBuilder) -> None:
    req = ns_builder.delete_collection("default", ListOptions(), DeleteOptions())
    assert req.method == "DELETE"


def test_delete_collection_url_namespaced(ns_builder: RequestBuilder) -> None:
    req = ns_builder.delete_collection("default", ListOptions(), DeleteOptions())
    assert req.url == "/api/v1/namespaces/default/pods"


def test_delete_collection_url_all_namespaces(ns_builder: RequestBuilder) -> None:
    req = ns_builder.delete_collection(None, ListOptions(), DeleteOptions())
    assert req.url == "/api/v1/pods"


def test_delete_collection_url_cluster_scoped(
    cluster_builder: RequestBuilder,
) -> None:
    req = cluster_builder.delete_collection(None, ListOptions(), DeleteOptions())
    assert req.url == "/api/v1/nodes"


def test_delete_collection_query_params_from_list_options(
    ns_builder: RequestBuilder,
) -> None:
    opts = ListOptions(label_selector="app=old", limit=10)
    req = ns_builder.delete_collection("default", opts, DeleteOptions())
    assert req.query_params == {"labelSelector": "app=old", "limit": "10"}


def test_delete_collection_query_params_default(ns_builder: RequestBuilder) -> None:
    req = ns_builder.delete_collection("default", ListOptions(), DeleteOptions())
    assert req.query_params is None


def test_delete_collection_body_from_delete_options(
    ns_builder: RequestBuilder,
) -> None:
    del_opts = DeleteOptions(
        grace_period_seconds=0,
        propagation_policy=PropagationPolicy.BACKGROUND,
    )
    req = ns_builder.delete_collection("default", ListOptions(), del_opts)
    assert req.body is not None
    body = json.loads(req.body)
    assert body == {"gracePeriodSeconds": 0, "propagationPolicy": "Background"}


def test_delete_collection_body_default_is_none(ns_builder: RequestBuilder) -> None:
    req = ns_builder.delete_collection("default", ListOptions(), DeleteOptions())
    assert req.body is None


@pytest.mark.parametrize("request_timeout,expected", _TIMEOUT_CASES_SHORT)
def test_delete_collection_timeout(
    ns_builder: RequestBuilder, request_timeout: object, expected: object
) -> None:
    kwargs = {} if request_timeout is ... else {"request_timeout": request_timeout}
    req = ns_builder.delete_collection(
        "default",
        ListOptions(),
        DeleteOptions(),
        **kwargs,  # type: ignore[arg-type]
    )
    _assert_timeout(req.timeout, expected)


def test_replace_method(ns_builder: RequestBuilder) -> None:
    req = ns_builder.replace("my-pod", "default", PostOptions(), data="{}")
    assert req.method == "PUT"


def test_replace_url_namespaced(ns_builder: RequestBuilder) -> None:
    req = ns_builder.replace("my-pod", "default", PostOptions(), data="{}")
    assert req.url == "/api/v1/namespaces/default/pods/my-pod"


def test_replace_url_cluster_scoped(cluster_builder: RequestBuilder) -> None:
    req = cluster_builder.replace("my-node", None, PostOptions(), data="{}")
    assert req.url == "/api/v1/nodes/my-node"


def test_replace_body_passthrough(ns_builder: RequestBuilder) -> None:
    body = '{"kind":"Pod","metadata":{"name":"my-pod"}}'
    req = ns_builder.replace("my-pod", "default", PostOptions(), data=body)
    assert req.body == body


def test_replace_query_params_default(ns_builder: RequestBuilder) -> None:
    req = ns_builder.replace("my-pod", "default", PostOptions(), data="{}")
    assert req.query_params is None


def test_replace_query_params_dry_run(ns_builder: RequestBuilder) -> None:
    opts = PostOptions(dry_run=True, field_manager="mgr")
    req = ns_builder.replace("my-pod", "default", opts, data="{}")
    assert req.query_params == {"dryRun": "All", "fieldManager": "mgr"}


@pytest.mark.parametrize("request_timeout,expected", _TIMEOUT_CASES_SHORT)
def test_replace_timeout(
    ns_builder: RequestBuilder, request_timeout: object, expected: object
) -> None:
    kwargs = {} if request_timeout is ... else {"request_timeout": request_timeout}
    req = ns_builder.replace("my-pod", "default", PostOptions(), data="{}", **kwargs)  # type: ignore[arg-type]
    _assert_timeout(req.timeout, expected)


def test_patch_method(ns_builder: RequestBuilder) -> None:
    patch = JsonPatch().add("/metadata/labels/new", "value")
    req = ns_builder.patch("my-pod", "default", PatchOptions(), patch)
    assert req.method == "PATCH"


def test_patch_url_namespaced(ns_builder: RequestBuilder) -> None:
    patch = JsonPatch().add("/metadata/labels/new", "value")
    req = ns_builder.patch("my-pod", "default", PatchOptions(), patch)
    assert req.url == "/api/v1/namespaces/default/pods/my-pod"


def test_patch_url_cluster_scoped(cluster_builder: RequestBuilder) -> None:
    patch = JsonPatch().add("/metadata/labels/new", "value")
    req = cluster_builder.patch("my-node", None, PatchOptions(), patch)
    assert req.url == "/api/v1/nodes/my-node"


def test_patch_body_json_patch(ns_builder: RequestBuilder) -> None:
    patch = JsonPatch().add("/metadata/labels/app", "web")
    req = ns_builder.patch("my-pod", "default", PatchOptions(), patch)
    assert req.body is not None
    body = json.loads(req.body)
    assert body == [{"op": "add", "path": "/metadata/labels/app", "value": "web"}]


@pytest.mark.parametrize("patch,expected_content_type", _PATCH_HEADERS_CASES)
def test_patch_headers(
    ns_builder: RequestBuilder, patch: object, expected_content_type: str
) -> None:
    req = ns_builder.patch("my-pod", "default", PatchOptions(), patch)  # type: ignore[arg-type]
    assert req.headers == {
        "accept": "application/json",
        "content-type": expected_content_type,
    }


def test_patch_query_params_default(ns_builder: RequestBuilder) -> None:
    patch = JsonPatch().add("/x", 1)
    req = ns_builder.patch("my-pod", "default", PatchOptions(), patch)
    assert req.query_params is None


def test_patch_query_params_force(ns_builder: RequestBuilder) -> None:
    patch = JsonPatch().add("/x", 1)
    req = ns_builder.patch("my-pod", "default", PatchOptions(force=True), patch)
    assert req.query_params is not None
    assert req.query_params["force"] == "true"


def test_patch_query_params_field_validation(ns_builder: RequestBuilder) -> None:
    patch = JsonPatch().add("/x", 1)
    opts = PatchOptions(field_validation=FieldValidation.STRICT)
    req = ns_builder.patch("my-pod", "default", opts, patch)
    assert req.query_params is not None
    assert req.query_params["fieldValidation"] == "Strict"


def test_patch_query_params_all(ns_builder: RequestBuilder) -> None:
    patch = JsonPatch().add("/x", 1)
    opts = PatchOptions(
        dry_run=True,
        field_manager="mgr",
        force=True,
        field_validation=FieldValidation.WARN,
    )
    req = ns_builder.patch("my-pod", "default", opts, patch)
    assert req.query_params == {
        "dryRun": "All",
        "fieldManager": "mgr",
        "force": "true",
        "fieldValidation": "Warn",
    }


@pytest.mark.parametrize("request_timeout,expected", _TIMEOUT_CASES_SHORT)
def test_patch_timeout(
    ns_builder: RequestBuilder, request_timeout: object, expected: object
) -> None:
    patch = JsonPatch().add("/x", 1)
    kwargs = {} if request_timeout is ... else {"request_timeout": request_timeout}
    req = ns_builder.patch("my-pod", "default", PatchOptions(), patch, **kwargs)  # type: ignore[arg-type]
    _assert_timeout(req.timeout, expected)


def test_watch_method(ns_builder: RequestBuilder) -> None:
    req = ns_builder.watch("default", WatchOptions())
    assert req.method == "GET"


def test_watch_url_namespaced(ns_builder: RequestBuilder) -> None:
    req = ns_builder.watch("default", WatchOptions())
    assert req.url == "/api/v1/namespaces/default/pods"


def test_watch_url_all_namespaces(ns_builder: RequestBuilder) -> None:
    req = ns_builder.watch(None, WatchOptions())
    assert req.url == "/api/v1/pods"


def test_watch_url_cluster_scoped(cluster_builder: RequestBuilder) -> None:
    req = cluster_builder.watch(None, WatchOptions())
    assert req.url == "/api/v1/nodes"


def test_watch_query_params_always_has_watch_true(ns_builder: RequestBuilder) -> None:
    req = ns_builder.watch("default", WatchOptions())
    assert req.query_params is not None
    assert req.query_params["watch"] == "true"


def test_watch_query_params_label_selector(ns_builder: RequestBuilder) -> None:
    req = ns_builder.watch("default", WatchOptions(label_selector="app=web"))
    assert req.query_params is not None
    assert req.query_params["labelSelector"] == "app=web"


def test_watch_query_params_allow_bookmarks(ns_builder: RequestBuilder) -> None:
    req = ns_builder.watch("default", WatchOptions(allow_bookmarks=True))
    assert req.query_params is not None
    assert req.query_params["allowBookmarks"] == "true"


def test_watch_query_params_send_initial_events(ns_builder: RequestBuilder) -> None:
    req = ns_builder.watch("default", WatchOptions(send_initial_events=True))
    assert req.query_params is not None
    assert req.query_params["sendInitialEvents"] == "true"


def test_watch_query_params_timeout_seconds(ns_builder: RequestBuilder) -> None:
    req = ns_builder.watch("default", WatchOptions(timeout_seconds=300))
    assert req.query_params is not None
    assert req.query_params["timeoutSeconds"] == "300"


def test_watch_query_params_all(ns_builder: RequestBuilder) -> None:
    opts = WatchOptions(
        label_selector="app=web",
        field_selector="metadata.name=my-pod",
        allow_bookmarks=True,
        send_initial_events=False,
        timeout_seconds=60,
    )
    req = ns_builder.watch("default", opts)
    assert req.query_params == {
        "watch": "true",
        "labelSelector": "app=web",
        "fieldSelector": "metadata.name=my-pod",
        "allowBookmarks": "true",
        "sendInitialEvents": "false",
        "timeoutSeconds": "60",
    }


def test_watch_resource_version_injection(ns_builder: RequestBuilder) -> None:
    req = ns_builder.watch("default", WatchOptions(), resource_version="12345")
    assert req.query_params is not None
    assert req.query_params["resourceVersion"] == "12345"


def test_watch_resource_version_none_not_injected(
    ns_builder: RequestBuilder,
) -> None:
    req = ns_builder.watch("default", WatchOptions())
    assert req.query_params is not None
    assert "resourceVersion" not in req.query_params


@pytest.mark.parametrize("request_timeout,expected", _TIMEOUT_CASES_SHORT)
def test_watch_timeout(
    ns_builder: RequestBuilder, request_timeout: object, expected: object
) -> None:
    kwargs = {} if request_timeout is ... else {"request_timeout": request_timeout}
    req = ns_builder.watch("default", WatchOptions(), **kwargs)  # type: ignore[arg-type]
    _assert_timeout(req.timeout, expected)
