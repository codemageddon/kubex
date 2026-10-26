"""Name/namespace validation and escaping shared by every request builder.

A missing name must never fall through to the collection URL (a DELETE there is
DELETECOLLECTION), and a name/namespace must never be able to address a
different path than the one it names.
"""

from __future__ import annotations

import inspect
import pathlib
import typing
from typing import Any, Callable

import pytest

from kubex.core.params import (
    AttachOptions,
    DeleteOptions,
    ExecOptions,
    GetOptions,
    ListOptions,
    LogOptions,
    PatchOptions,
    PortForwardOptions,
    PostOptions,
    WatchOptions,
)
from kubex.core.patch import JsonPatch, Patch
from kubex.core.request import Request
from kubex.core.request_builder import builder as builder_module
from kubex.core.request_builder._paths import path_segment
from kubex.core.request_builder.builder import RequestBuilder

# Builder methods that address a collection rather than one named object. Any
# public builder method not listed here must take a `name` and reject an empty
# one; adding a method that does neither fails `test_builder_methods_are_classified`.
_COLLECTION_METHODS = {
    "list",
    "create",
    "delete_collection",
    "watch",
    "list_metadata",
    "watch_metadata",
}

_OPTION_FACTORIES: dict[type, Callable[[], Any]] = {
    GetOptions: GetOptions,
    ListOptions: ListOptions,
    WatchOptions: WatchOptions,
    PostOptions: PostOptions,
    PatchOptions: PatchOptions,
    DeleteOptions: DeleteOptions,
    LogOptions: LogOptions,
    ExecOptions: lambda: ExecOptions(command=["true"]),
    AttachOptions: AttachOptions,
    PortForwardOptions: lambda: PortForwardOptions(ports=[80]),
}


def _builder_methods() -> list[str]:
    return sorted(
        name
        for name, member in inspect.getmembers(RequestBuilder, inspect.isfunction)
        if not name.startswith("_")
    )


def _call(builder: RequestBuilder, method: str, **overrides: Any) -> Request:
    """Call `method` with plausible values for every required parameter."""
    func = getattr(builder, method)
    hints = typing.get_type_hints(getattr(RequestBuilder, method))
    kwargs: dict[str, Any] = {}
    for param in inspect.signature(func).parameters.values():
        if param.default is not inspect.Parameter.empty:
            continue
        hint = hints.get(param.name)
        if param.name in overrides:
            kwargs[param.name] = overrides[param.name]
        elif param.name == "name":
            kwargs[param.name] = "obj"
        elif param.name == "namespace":
            kwargs[param.name] = "default"
        elif param.name == "subresource":
            kwargs[param.name] = "status"
        elif param.name == "data":
            kwargs[param.name] = "{}"
        elif hint is Patch:
            kwargs[param.name] = JsonPatch()
        elif isinstance(hint, type) and hint in _OPTION_FACTORIES:
            kwargs[param.name] = _OPTION_FACTORIES[hint]()
        else:  # pragma: no cover - surfaced as a test failure
            raise AssertionError(f"no test value for {method}({param.name}: {hint})")
    result = func(**kwargs)
    assert isinstance(result, Request)
    return result


def _takes(method: str, param: str) -> bool:
    return param in inspect.signature(getattr(RequestBuilder, method)).parameters


_NAMED_METHODS = [m for m in _builder_methods() if _takes(m, "name")]
_NAMESPACED_METHODS = [m for m in _builder_methods() if _takes(m, "namespace")]


def test_builder_methods_are_classified() -> None:
    unnamed = {m for m in _builder_methods() if not _takes(m, "name")}
    assert unnamed == _COLLECTION_METHODS
    # Sanity check the enumeration actually found the single-object methods.
    assert {
        "get",
        "delete",
        "patch",
        "replace",
        "get_subresource",
        "replace_subresource",
        "create_subresource",
        "patch_subresource",
        "logs",
        "stream_logs",
        "get_metadata",
        "patch_metadata",
        "exec_request",
        "attach_request",
        "portforward_request",
    } <= set(_NAMED_METHODS)


@pytest.mark.parametrize("method", _NAMED_METHODS)
def test_named_method_builds_with_valid_name(
    ns_builder: RequestBuilder, method: str
) -> None:
    req = _call(ns_builder, method)
    assert "/namespaces/default/pods/obj" in req.url


@pytest.mark.parametrize("method", _NAMED_METHODS)
@pytest.mark.parametrize("name", [None, ""], ids=["none", "empty"])
def test_named_method_rejects_empty_name(
    ns_builder: RequestBuilder, method: str, name: str | None
) -> None:
    with pytest.raises(ValueError, match="^resource name may not be empty$"):
        _call(ns_builder, method, name=name)


@pytest.mark.parametrize("method", _NAMED_METHODS)
@pytest.mark.parametrize(
    "name",
    [".", "..", "a/b", "../../x", "a%2Fb"],
    ids=["dot", "dotdot", "slash", "traversal", "percent"],
)
def test_named_method_rejects_invalid_name(
    ns_builder: RequestBuilder, method: str, name: str
) -> None:
    with pytest.raises(ValueError, match="invalid resource name"):
        _call(ns_builder, method, name=name)


@pytest.mark.parametrize("method", _NAMED_METHODS)
def test_named_method_rejects_empty_name_cluster_scoped(
    cluster_builder: RequestBuilder, method: str
) -> None:
    if method in {"exec_request", "attach_request", "portforward_request"}:
        pytest.skip("namespace-scoped only")
    with pytest.raises(ValueError, match="^resource name may not be empty$"):
        _call(cluster_builder, method, name="", namespace=None)


@pytest.mark.parametrize("method", _NAMESPACED_METHODS)
@pytest.mark.parametrize(
    ("namespace", "match"),
    [
        ("", "^namespace may not be empty$"),
        (".", "invalid namespace"),
        ("..", "invalid namespace"),
        ("a/b", "invalid namespace"),
        ("a%b", "invalid namespace"),
    ],
    ids=["empty", "dot", "dotdot", "slash", "percent"],
)
def test_namespaced_method_rejects_invalid_namespace(
    ns_builder: RequestBuilder, method: str, namespace: str, match: str
) -> None:
    with pytest.raises(ValueError, match=match):
        _call(ns_builder, method, namespace=namespace)


@pytest.mark.parametrize("method", _NAMED_METHODS)
@pytest.mark.parametrize(
    ("name", "encoded"),
    [
        ("weird#name", "weird%23name"),
        ("weird?name", "weird%3Fname"),
        ("weird name", "weird%20name"),
        ("weird:name", "weird%3Aname"),
        ("a.b-c_d~e", "a.b-c_d~e"),
    ],
    ids=["hash", "question", "space", "colon", "unreserved"],
)
def test_named_method_percent_encodes_name(
    ns_builder: RequestBuilder, method: str, name: str, encoded: str
) -> None:
    req = _call(ns_builder, method, name=name)
    assert f"/namespaces/default/pods/{encoded}" in req.url


@pytest.mark.parametrize("method", _NAMESPACED_METHODS)
def test_namespaced_method_percent_encodes_namespace(
    ns_builder: RequestBuilder, method: str
) -> None:
    req = _call(ns_builder, method, namespace="ns#1")
    assert req.url.startswith("/api/v1/namespaces/ns%231/pods")


def test_delete_url_with_name_is_never_the_collection(
    ns_builder: RequestBuilder,
) -> None:
    req = ns_builder.delete("obj", "default", DeleteOptions())
    assert req.url == "/api/v1/namespaces/default/pods/obj"
    with pytest.raises(ValueError):
        ns_builder.delete(None, "default", DeleteOptions())  # type: ignore[arg-type]


def test_exact_urls_for_escaped_segments(ns_builder: RequestBuilder) -> None:
    assert (
        ns_builder.get("weird?name", "ns#1", GetOptions()).url
        == "/api/v1/namespaces/ns%231/pods/weird%3Fname"
    )
    assert (
        ns_builder.get_subresource("status", "weird#name", "default").url
        == "/api/v1/namespaces/default/pods/weird%23name/status"
    )
    assert (
        ns_builder.logs("a b", "default", LogOptions()).url
        == "/api/v1/namespaces/default/pods/a%20b/log"
    )


def test_collection_url_none_namespace_is_all_namespaces(
    ns_builder: RequestBuilder,
) -> None:
    assert ns_builder.list(None, ListOptions()).url == "/api/v1/pods"


def test_invalid_subresource_rejected(ns_builder: RequestBuilder) -> None:
    with pytest.raises(ValueError, match="invalid subresource"):
        ns_builder.get_subresource("../exec", "obj", "default")


def test_path_segment_type_error() -> None:
    with pytest.raises(TypeError, match="resource name must be a str"):
        path_segment(42, "resource name")


def test_builders_never_call_resource_config_url_directly() -> None:
    """Every builder must go through `_paths` so validation cannot be bypassed."""
    package = pathlib.Path(builder_module.__file__).parent
    offenders = [
        path.name
        for path in package.glob("*.py")
        if path.name != "_paths.py" and ".url(" in path.read_text()
    ]
    assert offenders == []
