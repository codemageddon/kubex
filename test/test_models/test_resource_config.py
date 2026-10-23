from __future__ import annotations

from typing import ClassVar

from kubex_core.models.interfaces import NamespaceScopedEntity
from kubex_core.models.metadata import ObjectMetadata
from kubex_core.models.partial_object_meta import PartialObjectMetadata
from kubex_core.models.resource_config import ResourceConfig


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
