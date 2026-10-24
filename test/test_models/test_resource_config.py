from __future__ import annotations

import importlib
import pkgutil
from typing import ClassVar

import pytest

from kubex_core.models.base_entity import BaseEntity
from kubex_core.models.interfaces import NamespaceScopedEntity
from kubex_core.models.metadata import ObjectMetadata
from kubex_core.models.partial_object_meta import PartialObjectMetadata
from kubex_core.models.resource_config import ResourceConfig, guess_plural


class _Widget(NamespaceScopedEntity):
    api_version: str = "example.io/v1alpha1"
    kind: str = "Widget"
    metadata: ObjectMetadata


class _Gadget(NamespaceScopedEntity):
    api_version: str = "other.io/v1"
    kind: str = "Gadget"
    metadata: ObjectMetadata


def test_config_less_subclasses_do_not_share_resource_config() -> None:
    assert _Widget.__RESOURCE_CONFIG__.url("ns") == (
        "/apis/example.io/v1alpha1/namespaces/ns/widgets"
    )
    assert (
        _Gadget.__RESOURCE_CONFIG__.url("ns")
        == "/apis/other.io/v1/namespaces/ns/gadgets"
    )
    widget_config: object = _Widget.__RESOURCE_CONFIG__
    gadget_config: object = _Gadget.__RESOURCE_CONFIG__
    assert widget_config is not gadget_config


def test_config_less_subclass_is_unaffected_by_partial_object_metadata() -> None:
    # Accessing PartialObjectMetadata's own, explicitly-declared config must not
    # prime the shared BaseEntity default that config-less subclasses inherit.
    assert PartialObjectMetadata.__RESOURCE_CONFIG__.plural == "partialobjectmetadatas"

    class _Other(NamespaceScopedEntity):
        api_version: str = "later.io/v1"
        kind: str = "Other"
        metadata: ObjectMetadata

    assert (
        _Other.__RESOURCE_CONFIG__.url("ns") == "/apis/later.io/v1/namespaces/ns/others"
    )


def test_declared_resource_config_is_reused_across_accesses() -> None:
    class _Declared(NamespaceScopedEntity):
        __RESOURCE_CONFIG__: ClassVar[ResourceConfig["_Declared"]] = ResourceConfig[
            "_Declared"
        ](
            version="v1",
            kind="Declared",
            group="core",
            plural="declareds",
        )
        api_version: str = "v1"
        kind: str = "Declared"
        metadata: ObjectMetadata

    first = _Declared.__RESOURCE_CONFIG__
    second = _Declared.__RESOURCE_CONFIG__
    assert first is second
    assert first.url("ns") == "/api/v1/namespaces/ns/declareds"


@pytest.mark.parametrize(
    ("kind", "plural"),
    [
        ("Widget", "widgets"),
        ("Gateway", "gateways"),
        ("Key", "keys"),
        ("Policy", "policies"),
        ("Proxy", "proxies"),
        ("Mesh", "meshes"),
        ("Patch", "patches"),
        ("Ingress", "ingresses"),
        ("Box", "boxes"),
        ("Status", "statuses"),
        ("Endpoints", "endpoints"),
        ("CustomEndpoints", "customendpoints"),
    ],
)
def test_guess_plural(kind: str, plural: str) -> None:
    assert guess_plural(kind) == plural


def test_auto_plural_used_for_config_less_entity() -> None:
    class _Gateway(NamespaceScopedEntity):
        api_version: str = "gateway.example.io/v1"
        kind: str = "Gateway"
        metadata: ObjectMetadata

    assert _Gateway.__RESOURCE_CONFIG__.url("ns") == (
        "/apis/gateway.example.io/v1/namespaces/ns/gateways"
    )


def test_guess_plural_matches_builtin_resources() -> None:
    """The guesser agrees with every plural the API server declares."""
    import kubex.k8s.v1_35 as root

    checked = 0
    for info in pkgutil.walk_packages(root.__path__, root.__name__ + "."):
        module = importlib.import_module(info.name)
        for obj in vars(module).values():
            if (
                isinstance(obj, type)
                and issubclass(obj, BaseEntity)
                and obj.__module__ == module.__name__
                and "__RESOURCE_CONFIG__" in obj.__dict__
            ):
                config = obj.__RESOURCE_CONFIG__
                assert guess_plural(config.kind) == config.plural, config.kind
                checked += 1
    assert checked > 50


def test_subclass_builds_its_own_list_model() -> None:
    """A subclass of a resolved resource must not inherit the parent's list model."""
    from kubex.k8s.v1_35.core.v1.pod import Pod
    from kubex.k8s.v1_35.core.v1.pod_list import PodList

    assert Pod.__RESOURCE_CONFIG__.list_model is PodList

    class _MyPod(Pod):
        pass

    list_model = _MyPod.__RESOURCE_CONFIG__.list_model
    assert list_model is not PodList
    listed = list_model.model_validate(
        {
            "apiVersion": "v1",
            "kind": "PodList",
            "metadata": {},
            "items": [{"metadata": {"name": "a"}}],
        }
    )
    assert type(listed.items[0]) is _MyPod
    assert _MyPod.__RESOURCE_CONFIG__.url("ns") == "/api/v1/namespaces/ns/pods"
    # The parent's config is untouched.
    assert Pod.__RESOURCE_CONFIG__.list_model is PodList


def test_subclass_of_config_less_entity_builds_its_own_list_model() -> None:
    class _Base(NamespaceScopedEntity):
        api_version: str = "example.io/v1"
        kind: str = "Thing"
        metadata: ObjectMetadata

    base_list = _Base.__RESOURCE_CONFIG__.list_model

    class _Child(_Base):
        pass

    child_list = _Child.__RESOURCE_CONFIG__.list_model
    assert child_list is not base_list
    listed = child_list.model_validate(
        {
            "apiVersion": "example.io/v1",
            "kind": "ThingList",
            "metadata": {},
            "items": [{"metadata": {}}],
        }
    )
    assert type(listed.items[0]) is _Child


def test_generated_list_model_reads_null_items() -> None:
    class _Thing(NamespaceScopedEntity):
        api_version: str = "example.io/v1"
        kind: str = "Thing"
        metadata: ObjectMetadata

    listed = _Thing.__RESOURCE_CONFIG__.list_model.model_validate(
        {
            "apiVersion": "example.io/v1",
            "kind": "ThingList",
            "metadata": {},
            "items": None,
        }
    )
    assert listed.items == []
