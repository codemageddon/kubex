from __future__ import annotations

from typing import Any

import pytest

from scripts.codegen.naming import py_field_name
from scripts.codegen.type_mapper import MappedType, map_type


def _map(
    schema: dict[str, Any],
    *,
    prop: str = "field",
    owner: str = "io.k8s.api.core.v1.Owner",
) -> MappedType:
    return map_type(
        schema,
        k8s_version_tag="v1_30",
        owner_definition=owner,
        owner_module=f"kubex.k8s.v1_30.core.v1.{py_field_name(owner.rsplit('.', 1)[-1])}",
        property_name=prop,
    )


def test_primitives() -> None:
    assert _map({"type": "string"}).expression == "str"
    assert _map({"type": "integer"}).expression == "int"
    assert _map({"type": "boolean"}).expression == "bool"
    assert _map({"type": "number"}).expression == "float"


def test_string_formats() -> None:
    dt = _map({"type": "string", "format": "date-time"})
    assert dt.expression == "Time"
    assert dt.nullable is True
    assert any(
        x.module == "kubex_core.models.types" and x.class_name == "Time"
        for x in dt.cross_refs
    )
    byte = _map({"type": "string", "format": "byte"})
    assert byte.expression == "str"
    # A nil Go []byte marshals as `null`.
    assert byte.nullable is True
    ios = _map({"type": "string", "format": "int-or-string"})
    assert ios.expression == "IntOrString"
    assert ios.nullable is False
    assert any(x.class_name == "IntOrString" for x in ios.cross_refs)
    assert _map({"type": "string"}).nullable is False


def test_array_and_map() -> None:
    arr = _map({"type": "array", "items": {"type": "string"}})
    assert arr.expression == "list[str]"
    assert (arr.container, arr.item_expression) == ("list", "str")
    d = _map({"type": "object", "additionalProperties": {"type": "integer"}})
    assert d.expression == "dict[str, int]"
    assert (d.container, d.item_expression) == ("dict", "int")
    free = _map({"type": "object"})
    assert free.expression == "dict[str, Any]"
    assert (free.container, free.item_expression) == ("dict", "Any")


def test_container_does_not_inherit_item_nullability() -> None:
    times = _map(
        {
            "type": "array",
            "items": {
                "$ref": "#/definitions/io.k8s.apimachinery.pkg.apis.meta.v1.Time"
            },
        }
    )
    assert times.expression == "list[Time]"
    assert times.nullable is False
    assert times.item_expression == "Time"
    assert any(x.class_name == "Time" for x in times.cross_refs)


def test_enum_generates_request() -> None:
    out = _map(
        {"type": "string", "enum": ["A", "B"]},
        prop="phase",
        owner="io.k8s.api.core.v1.Pod",
    )
    assert out.expression == "PodPhase"
    assert len(out.enum_requests) == 1
    req = out.enum_requests[0]
    assert req.class_name == "PodPhase"
    assert req.values == ("A", "B")


def test_ref_override_to_kubex_core() -> None:
    out = _map(
        {"$ref": "#/definitions/io.k8s.apimachinery.pkg.apis.meta.v1.ObjectMeta"}
    )
    assert out.expression == "ObjectMetadata"
    assert any(x.module == "kubex_core.models.metadata" for x in out.cross_refs)


def test_ref_alias_intorstring() -> None:
    out = _map(
        {"$ref": "#/definitions/io.k8s.apimachinery.pkg.util.intstr.IntOrString"}
    )
    assert out.expression == "int | str"


def test_ref_to_different_class_is_cross_ref() -> None:
    out = _map(
        {"$ref": "#/definitions/io.k8s.api.core.v1.NodeAddress"},
        owner="io.k8s.api.core.v1.NodeStatus",
    )
    assert out.expression == "NodeAddress"
    assert any(
        x.class_name == "NodeAddress"
        and x.module == "kubex.k8s.v1_30.core.v1.node_address"
        for x in out.cross_refs
    )


@pytest.mark.parametrize(
    ("definition", "expression", "nullable"),
    [
        ("io.k8s.apimachinery.pkg.api.resource.Quantity", "Quantity", False),
        ("io.k8s.apimachinery.pkg.apis.meta.v1.Time", "Time", True),
        ("io.k8s.apimachinery.pkg.apis.meta.v1.MicroTime", "MicroTime", True),
    ],
)
def test_ref_alias_to_kubex_core_types(
    definition: str, expression: str, nullable: bool
) -> None:
    out = _map({"$ref": f"#/definitions/{definition}"})
    assert out.expression == expression
    assert out.nullable is nullable
    assert [(x.module, x.class_name) for x in out.cross_refs] == [
        ("kubex_core.models.types", expression)
    ]
    assert not out.stdlib_imports


def test_ref_alias_raw_extension_is_nullable_dict() -> None:
    out = _map({"$ref": "#/definitions/io.k8s.apimachinery.pkg.runtime.RawExtension"})
    assert out.expression == "dict[str, Any]"
    assert out.nullable is True
    assert "Any" in out.typing_imports


_APIEXT = "io.k8s.apiextensions-apiserver.pkg.apis.apiextensions.v1"
_PROPS_MODULE = "kubex.k8s.v1_30.apiextensions_k8s_io.v1.json_schema_props"


@pytest.mark.parametrize(
    ("short", "expression"),
    [
        ("JSON", "Any"),
        ("JSONSchemaPropsOrBool", "JSONSchemaProps | bool"),
        ("JSONSchemaPropsOrArray", "JSONSchemaProps | list[JSONSchemaProps]"),
        ("JSONSchemaPropsOrStringArray", "JSONSchemaProps | list[str]"),
    ],
)
def test_ref_alias_apiextensions_json_types(short: str, expression: str) -> None:
    ref = {"$ref": f"#/definitions/{_APIEXT}.{short}"}
    # From inside JSONSchemaProps' own module: no import needed.
    same = map_type(
        ref,
        k8s_version_tag="v1_30",
        owner_definition=f"{_APIEXT}.JSONSchemaProps",
        owner_module=_PROPS_MODULE,
        property_name="items",
    )
    assert same.expression == expression
    assert not any(x.class_name == "JSONSchemaProps" for x in same.cross_refs)
    # From another module the class is imported.
    other = _map(ref)
    assert other.expression == expression
    if "JSONSchemaProps" in expression:
        assert any(
            x.module == _PROPS_MODULE and x.class_name == "JSONSchemaProps"
            for x in other.cross_refs
        )
    else:
        assert "Any" in other.typing_imports


def test_ref_to_schema_less_definition_maps_to_any() -> None:
    definitions: dict[str, Any] = {
        "io.k8s.api.core.v1.Opaque": {"description": "Anything goes."},
        "io.k8s.api.core.v1.Typed": {"type": "object", "properties": {}},
    }
    opaque = map_type(
        {"$ref": "#/definitions/io.k8s.api.core.v1.Opaque"},
        k8s_version_tag="v1_30",
        owner_definition="io.k8s.api.core.v1.Owner",
        owner_module="kubex.k8s.v1_30.core.v1.owner",
        property_name="value",
        definitions=definitions,
    )
    assert opaque.expression == "Any"
    assert "Any" in opaque.typing_imports
    assert not opaque.cross_refs
    typed = map_type(
        {"$ref": "#/definitions/io.k8s.api.core.v1.Typed"},
        k8s_version_tag="v1_30",
        owner_definition="io.k8s.api.core.v1.Owner",
        owner_module="kubex.k8s.v1_30.core.v1.owner",
        property_name="value",
        definitions=definitions,
    )
    assert typed.expression == "Typed"
