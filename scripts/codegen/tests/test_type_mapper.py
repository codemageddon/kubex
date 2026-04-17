from __future__ import annotations

from typing import Any

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
        owner_module="kubex.k8s.v1_30.core_v1",
        property_name=prop,
    )


def test_primitives() -> None:
    assert _map({"type": "string"}).expression == "str"
    assert _map({"type": "integer"}).expression == "int"
    assert _map({"type": "boolean"}).expression == "bool"
    assert _map({"type": "number"}).expression == "float"


def test_string_formats() -> None:
    dt = _map({"type": "string", "format": "date-time"})
    assert dt.expression == "datetime.datetime"
    assert ("datetime", "datetime") in dt.stdlib_imports
    assert _map({"type": "string", "format": "byte"}).expression == "str"
    ios = _map({"type": "string", "format": "int-or-string"})
    assert ios.expression == "IntOrString"
    assert any(x.class_name == "IntOrString" for x in ios.cross_refs)


def test_array_and_map() -> None:
    arr = _map({"type": "array", "items": {"type": "string"}})
    assert arr.expression == "list[str]"
    d = _map({"type": "object", "additionalProperties": {"type": "integer"}})
    assert d.expression == "dict[str, int]"


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


def test_ref_to_same_module_is_local() -> None:
    out = _map(
        {"$ref": "#/definitions/io.k8s.api.core.v1.NodeAddress"},
        owner="io.k8s.api.core.v1.NodeStatus",
    )
    assert out.expression == "NodeAddress"
    assert "NodeAddress" in out.local_refs
