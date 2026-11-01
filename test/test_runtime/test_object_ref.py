"""``ObjectRef``: building references from models, objects and owner references."""

from __future__ import annotations

from typing import ClassVar

import pytest

from kubex.k8s.v1_35.apps.v1.deployment import Deployment
from kubex.k8s.v1_35.core.v1.config_map import ConfigMap
from kubex.k8s.v1_35.core.v1.namespace import Namespace
from kubex_core.models.interfaces import NamespaceScopedEntity
from kubex_core.models.metadata import ObjectMetadata
from kubex_core.models.resource_config import ResourceConfig
from kubex_runtime import ObjectRef
from test.test_runtime._fakes import cm, owner


def test_of_core_kind() -> None:
    ref = ObjectRef.of(ConfigMap, "a", "ns")
    assert ref == ObjectRef(group="core", kind="ConfigMap", name="a", namespace="ns")


def test_of_grouped_kind() -> None:
    ref = ObjectRef.of(Deployment, "web", "ns")
    assert ref == ObjectRef(group="apps", kind="Deployment", name="web", namespace="ns")


def test_of_cluster_scoped_kind_defaults_to_no_namespace() -> None:
    ref = ObjectRef.of(Namespace, "tenant")
    assert ref.namespace is None
    assert ref.kind == "Namespace"


def test_from_obj() -> None:
    assert ObjectRef.from_obj(cm("a", namespace="other")) == ObjectRef.of(
        ConfigMap, "a", "other"
    )


def test_from_obj_cluster_scoped() -> None:
    namespace = Namespace(metadata=ObjectMetadata(name="tenant"))
    assert ObjectRef.from_obj(namespace) == ObjectRef.of(Namespace, "tenant")


@pytest.mark.parametrize("name", [None, ""])
def test_from_obj_without_name_raises(name: str | None) -> None:
    obj = ConfigMap(metadata=ObjectMetadata(name=name, namespace="ns"))
    with pytest.raises(ValueError, match="ConfigMap has no name"):
        ObjectRef.from_obj(obj)


def test_from_owner_core_group() -> None:
    ref = ObjectRef.from_owner(owner("ConfigMap", "parent"), "ns")
    assert ref == ObjectRef(
        group="core", kind="ConfigMap", name="parent", namespace="ns"
    )
    assert ref == ObjectRef.of(ConfigMap, "parent", "ns")


def test_from_owner_grouped_api_version() -> None:
    ref = ObjectRef.from_owner(owner("Deployment", "web", api_version="apps/v1"), "ns")
    assert ref == ObjectRef(group="apps", kind="Deployment", name="web", namespace="ns")
    assert ref == ObjectRef.of(Deployment, "web", "ns")


def test_from_owner_cluster_scoped() -> None:
    ref = ObjectRef.from_owner(owner("Namespace", "tenant"), None)
    assert ref == ObjectRef.of(Namespace, "tenant")


def test_from_owner_defaults_to_no_namespace() -> None:
    assert ObjectRef.from_owner(owner("Namespace", "tenant")).namespace is None


def test_is_kind_of() -> None:
    ref = ObjectRef.of(ConfigMap, "a", "ns")
    assert ref.is_kind_of(ConfigMap)
    assert not ref.is_kind_of(Deployment)
    assert not ref.is_kind_of(Namespace)


def test_is_kind_of_compares_group() -> None:
    # same kind name, other group
    ref = ObjectRef(group="example.com", kind="Deployment", name="web", namespace="ns")
    assert not ref.is_kind_of(Deployment)


def test_equal_refs_are_one_key() -> None:
    first = ObjectRef.of(ConfigMap, "a", "ns")
    second = ObjectRef.from_obj(cm("a"))
    assert first == second
    assert hash(first) == hash(second)
    assert {first: 1}[second] == 1
    assert ObjectRef.of(ConfigMap, "a", "other") != first


def test_str_namespaced() -> None:
    assert str(ObjectRef.of(ConfigMap, "a", "ns")) == "ConfigMap.core ns/a"


def test_str_cluster_scoped() -> None:
    assert str(ObjectRef.of(Namespace, "tenant")) == "Namespace.core tenant"


def test_the_core_group_given_as_empty_is_kept_as_core() -> None:
    # Kubernetes and kube-rs spell the core group "": a reference built that way
    # must be the same key as the controller's own
    ref = ObjectRef(group="", kind="ConfigMap", name="a", namespace="ns")
    assert ref.group == "core"
    assert ref == ObjectRef.of(ConfigMap, "a", "ns")
    assert hash(ref) == hash(ObjectRef.of(ConfigMap, "a", "ns"))
    assert ref.is_kind_of(ConfigMap)
    assert str(ref) == "ConfigMap.core ns/a"


class _EmptyGroupThing(NamespaceScopedEntity):
    """A hand-written core model that spells its group "", as Kubernetes does."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["_EmptyGroupThing"]] = ResourceConfig[
        "_EmptyGroupThing"
    ](version="v1", kind="Thing", group="", plural="things")
    api_version: str = "v1"
    kind: str = "Thing"
    metadata: ObjectMetadata


def test_a_model_with_an_empty_core_group() -> None:
    owned_by = ObjectRef.from_owner(owner("Thing", "x"), "ns")
    assert owned_by.is_kind_of(_EmptyGroupThing)
    assert ObjectRef.of(_EmptyGroupThing, "x", "ns") == owned_by
