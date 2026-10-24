from __future__ import annotations

from typing import Any

import pytest

from scripts.codegen.ref_resolver import (
    OVERRIDES,
    OverrideDriftError,
    collect_override_field_sets,
    is_opaque_schema,
    module_for_definition,
    resolve,
    validate_overrides,
)

_OBJECT_META = "io.k8s.apimachinery.pkg.apis.meta.v1.ObjectMeta"

# ObjectMeta as published in the 1.35 spec.
_OBJECT_META_PROPERTIES = [
    "annotations",
    "creationTimestamp",
    "deletionGracePeriodSeconds",
    "deletionTimestamp",
    "finalizers",
    "generateName",
    "generation",
    "labels",
    "managedFields",
    "name",
    "namespace",
    "ownerReferences",
    "resourceVersion",
    "selfLink",
    "uid",
]


@pytest.mark.parametrize(
    ("definition", "expected_module", "expected_cls"),
    [
        (
            "io.k8s.api.core.v1.Pod",
            "kubex.k8s.v1_30.core.v1.pod",
            "Pod",
        ),
        (
            "io.k8s.api.core.v1.PersistentVolumeClaim",
            "kubex.k8s.v1_30.core.v1.persistent_volume_claim",
            "PersistentVolumeClaim",
        ),
        (
            "io.k8s.api.apps.v1.Deployment",
            "kubex.k8s.v1_30.apps.v1.deployment",
            "Deployment",
        ),
        (
            "io.k8s.api.networking.v1.Ingress",
            "kubex.k8s.v1_30.networking.v1.ingress",
            "Ingress",
        ),
    ],
)
def test_module_for_definition_api(
    definition: str, expected_module: str, expected_cls: str
) -> None:
    module, cls = module_for_definition(definition, k8s_version_tag="v1_30")
    assert module == expected_module
    assert cls == expected_cls


@pytest.mark.parametrize(
    ("definition", "expected_module", "expected_cls"),
    [
        (
            "io.k8s.apiextensions-apiserver.pkg.apis.apiextensions.v1.CustomResourceDefinition",
            "kubex.k8s.v1_30.apiextensions_k8s_io.v1.custom_resource_definition",
            "CustomResourceDefinition",
        ),
        (
            "io.k8s.kube-aggregator.pkg.apis.apiregistration.v1.APIService",
            "kubex.k8s.v1_30.apiregistration.v1.api_service",
            "APIService",
        ),
        (
            "io.k8s.apimachinery.pkg.apis.meta.v1.Status",
            "kubex.k8s.v1_30.meta.v1.status",
            "Status",
        ),
    ],
)
def test_module_for_definition_non_api(
    definition: str, expected_module: str, expected_cls: str
) -> None:
    module, cls = module_for_definition(definition, k8s_version_tag="v1_30")
    assert module == expected_module
    assert cls == expected_cls


def test_resolve_override_unchanged() -> None:
    r = resolve(
        "io.k8s.apimachinery.pkg.apis.meta.v1.ObjectMeta", k8s_version_tag="v1_30"
    )
    assert r.is_override is True
    assert r.module == "kubex_core.models.metadata"
    assert r.class_name == "ObjectMetadata"


def test_resolve_alias_unchanged() -> None:
    r = resolve(
        "io.k8s.apimachinery.pkg.util.intstr.IntOrString", k8s_version_tag="v1_30"
    )
    assert r.is_alias is True
    assert r.alias is not None
    assert r.alias.expression == "int | str"


def test_resolve_quantity_alias_uses_kubex_core_type() -> None:
    r = resolve(
        "io.k8s.apimachinery.pkg.api.resource.Quantity", k8s_version_tag="v1_30"
    )
    assert r.is_alias is True
    assert r.alias is not None
    assert r.alias.expression == "Quantity"
    assert r.alias.from_imports == (("kubex_core.models.types", "Quantity"),)


@pytest.mark.parametrize(
    ("schema", "opaque"),
    [
        ({"description": "JSON represents any valid JSON value."}, True),
        ({}, True),
        ({"type": "object"}, False),
        ({"type": "string", "format": "int-or-string"}, False),
        ({"properties": {"a": {"type": "string"}}}, False),
        ({"allOf": [{"$ref": "#/definitions/x"}]}, False),
    ],
)
def test_is_opaque_schema(schema: dict[str, Any], opaque: bool) -> None:
    assert is_opaque_schema(schema) is opaque


def test_resolve_schema_less_definition_needs_definitions() -> None:
    name = "io.k8s.api.core.v1.Opaque"
    definitions: dict[str, Any] = {name: {"description": "no schema"}}
    aliased = resolve(name, k8s_version_tag="v1_30", definitions=definitions)
    assert aliased.is_alias is True
    assert aliased.alias is not None
    assert aliased.alias.expression == "Any"
    # Without the definitions map it is an ordinary generated class.
    plain = resolve(name, k8s_version_tag="v1_30")
    assert plain.is_alias is False
    assert plain.class_name == "Opaque"


def test_override_field_sets_cover_current_object_meta() -> None:
    field_sets = collect_override_field_sets()
    assert set(field_sets) == set(OVERRIDES)
    assert set(_OBJECT_META_PROPERTIES) <= field_sets[_OBJECT_META]
    assert "continue" in field_sets["io.k8s.apimachinery.pkg.apis.meta.v1.ListMeta"]


def test_validate_overrides_accepts_matching_spec() -> None:
    definitions: dict[str, Any] = {
        _OBJECT_META: {
            "type": "object",
            "properties": {p: {"type": "string"} for p in _OBJECT_META_PROPERTIES},
        },
        "io.k8s.apimachinery.pkg.apis.meta.v1.ListMeta": {
            "type": "object",
            "properties": {
                "continue": {"type": "string"},
                "remainingItemCount": {"type": "integer"},
                "resourceVersion": {"type": "string"},
                "selfLink": {"type": "string"},
                "shardInfo": {"type": "object"},
            },
        },
    }
    validate_overrides(definitions)


def test_validate_overrides_reports_drift() -> None:
    definitions: dict[str, Any] = {
        _OBJECT_META: {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "futureField": {"type": "string"},
            },
        },
    }
    with pytest.raises(OverrideDriftError, match="futureField"):
        validate_overrides(definitions)
    # Explicit field sets override the introspected ones.
    validate_overrides(
        definitions, override_field_sets={_OBJECT_META: {"name", "futureField"}}
    )


def test_override_drift_error_is_a_value_error() -> None:
    # The `generate` CLI turns ValueError into a clean error + exit code 1.
    assert issubclass(OverrideDriftError, ValueError)
