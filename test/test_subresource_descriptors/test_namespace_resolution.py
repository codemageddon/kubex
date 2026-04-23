from __future__ import annotations

import pytest

from kubex.api._protocol import (
    ensure_optional_namespace,
    ensure_required_namespace,
    get_namespace,
)
from kubex_core.models.resource_config import Scope


@pytest.mark.parametrize(
    ("namespace", "default", "expected"),
    [
        (..., "default", "default"),
        ("custom", "default", "custom"),
        (None, "default", None),
    ],
    ids=["ellipsis-uses-default", "override", "none-override"],
)
def test_get_namespace(
    namespace: str | None, default: str | None, expected: str | None
) -> None:
    assert get_namespace(namespace, default) == expected


@pytest.mark.parametrize(
    ("namespace", "default", "scope", "expected"),
    [
        (..., "default", Scope.NAMESPACE, "default"),
        (None, None, Scope.CLUSTER, None),
    ],
    ids=["ellipsis-resolves-for-namespaced", "none-for-cluster-scoped"],
)
def test_ensure_required_namespace(
    namespace: str | None, default: str | None, scope: Scope, expected: str | None
) -> None:
    assert ensure_required_namespace(namespace, default, scope) == expected


@pytest.mark.parametrize(
    ("namespace", "default", "scope", "match"),
    [
        (None, None, Scope.NAMESPACE, "Namespace is required"),
        (
            "ns",
            "ns",
            Scope.CLUSTER,
            "Namespace is not supported for cluster-scoped resources",
        ),
        (..., None, Scope.NAMESPACE, "Namespace is required"),
    ],
    ids=[
        "none-for-namespaced",
        "given-for-cluster-scoped",
        "ellipsis-default-none-for-namespaced",
    ],
)
def test_ensure_required_namespace_raises(
    namespace: str | None, default: str | None, scope: Scope, match: str
) -> None:
    with pytest.raises(ValueError, match=match):
        ensure_required_namespace(namespace, default, scope)


@pytest.mark.parametrize(
    ("namespace", "default", "scope", "expected"),
    [
        (None, None, Scope.NAMESPACE, None),
        (None, None, Scope.CLUSTER, None),
        (..., "default", Scope.NAMESPACE, "default"),
    ],
    ids=[
        "none-for-namespaced",
        "none-for-cluster-scoped",
        "ellipsis-resolves-for-namespaced",
    ],
)
def test_ensure_optional_namespace(
    namespace: str | None, default: str | None, scope: Scope, expected: str | None
) -> None:
    assert ensure_optional_namespace(namespace, default, scope) == expected


@pytest.mark.parametrize(
    ("namespace", "default", "scope", "match"),
    [
        (
            "ns",
            "ns",
            Scope.CLUSTER,
            "Namespace is not supported for cluster-scoped resources",
        ),
    ],
    ids=["given-for-cluster-scoped"],
)
def test_ensure_optional_namespace_raises(
    namespace: str | None, default: str | None, scope: Scope, match: str
) -> None:
    with pytest.raises(ValueError, match=match):
        ensure_optional_namespace(namespace, default, scope)
