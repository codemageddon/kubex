"""Field emission rules for spec-required fields the server may send as null."""

from __future__ import annotations

from typing import Any

import pytest

from scripts.codegen import model_emitter, resource_detector
from scripts.codegen.ir import BuildResult, EmittedField
from scripts.codegen.package_builder import _render_field
from scripts.codegen.ref_resolver import OverrideDriftError

_META = "io.k8s.apimachinery.pkg.apis.meta.v1"
_APIEXT = "io.k8s.apiextensions-apiserver.pkg.apis.apiextensions.v1"


def _build(
    definitions: dict[str, Any], paths: dict[str, Any] | None = None
) -> BuildResult:
    resources = resource_detector.detect_resources(definitions, paths or {})
    return model_emitter.build_modules(
        k8s_version_tag="v1_30", definitions=definitions, resources=resources
    )


def _widget_definitions() -> dict[str, Any]:
    ref = "#/definitions/"
    return {
        f"{_META}.Time": {"type": "string", "format": "date-time"},
        f"{_META}.MicroTime": {"type": "string", "format": "date-time"},
        "io.k8s.apimachinery.pkg.runtime.RawExtension": {"type": "object"},
        "io.k8s.api.example.v1.Item": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
        },
        "io.k8s.api.example.v1.Widget": {
            "type": "object",
            "required": [
                "items",
                "labels",
                "free",
                "observed",
                "renewed",
                "payload",
                "raw",
                "name",
                "count",
                "enabled",
                "item",
            ],
            "properties": {
                "apiVersion": {"type": "string"},
                "kind": {"type": "string"},
                "metadata": {"$ref": f"{ref}{_META}.ObjectMeta"},
                "items": {
                    "type": "array",
                    "items": {"$ref": f"{ref}io.k8s.api.example.v1.Item"},
                },
                "labels": {
                    "type": "object",
                    "additionalProperties": {"type": "string"},
                },
                "free": {"type": "object"},
                "observed": {"$ref": f"{ref}{_META}.Time"},
                "renewed": {"$ref": f"{ref}{_META}.MicroTime"},
                "payload": {"type": "string", "format": "byte"},
                "raw": {"$ref": f"{ref}io.k8s.apimachinery.pkg.runtime.RawExtension"},
                "name": {"type": "string"},
                "count": {"type": "integer"},
                "enabled": {"type": "boolean"},
                "item": {"$ref": f"{ref}io.k8s.api.example.v1.Item"},
                "optionalItems": {"type": "array", "items": {"type": "string"}},
                "optionalTime": {"$ref": f"{ref}{_META}.Time"},
            },
            "x-kubernetes-group-version-kind": [
                {"group": "example", "kind": "Widget", "version": "v1"}
            ],
        },
    }


_WIDGET_PATHS: dict[str, Any] = {
    "/apis/example/v1/namespaces/{namespace}/widgets/{name}": {
        "get": {
            "x-kubernetes-group-version-kind": {
                "group": "example",
                "kind": "Widget",
                "version": "v1",
            }
        }
    }
}


def _widget_fields() -> tuple[dict[str, EmittedField], str]:
    build = _build(_widget_definitions(), _WIDGET_PATHS)
    module = build.modules["kubex.k8s.v1_30.example.v1.widget"]
    fields = {f.alias: f for f in module.classes[0].fields}
    return fields, module.imports.render()


@pytest.mark.parametrize(
    ("alias", "rendered_annotation"),
    [
        # Collections keep their type but read null as empty.
        ("items", "NullAsEmptyList[Item] = Field(...,"),
        ("labels", "NullAsEmptyDict[str] = Field(...,"),
        ("free", "NullAsEmptyDict[Any] = Field(...,"),
        # Go types whose zero value marshals as null: required but nullable.
        ("observed", "Time | None = Field(...,"),
        ("renewed", "MicroTime | None = Field(...,"),
        ("payload", "str | None = Field(...,"),
        ("raw", "dict[str, Any] | None = Field(...,"),
        # Plain scalars and structs stay strictly required.
        ("name", "str = Field(...,"),
        ("count", "int = Field(...,"),
        ("enabled", "bool = Field(...,"),
        ("item", "Item = Field(...,"),
        # Optional fields are unchanged.
        ("optionalItems", "list[str] | None = Field(default=None,"),
        ("optionalTime", "Time | None = Field(default=None,"),
    ],
)
def test_required_field_null_handling(alias: str, rendered_annotation: str) -> None:
    fields, _ = _widget_fields()
    rendered = _render_field(fields[alias], "Widget")
    assert rendered_annotation in rendered, rendered


def test_required_field_imports() -> None:
    _, imports = _widget_fields()
    assert (
        "from kubex_core.models.types import MicroTime, NullAsEmptyDict, "
        "NullAsEmptyList, Time" in imports
    )
    assert "import datetime" not in imports


def test_literal_api_version_and_kind_are_not_wrapped() -> None:
    fields, _ = _widget_fields()
    assert fields["kind"].type_expression == 'Literal["Widget"]'
    assert fields["kind"].nullable is False


def test_apiextensions_json_types_are_aliased_not_emitted() -> None:
    ref = "#/definitions/"
    definitions: dict[str, Any] = {
        f"{_APIEXT}.JSON": {"description": "any JSON value"},
        f"{_APIEXT}.JSONSchemaPropsOrBool": {"description": "props or bool"},
        f"{_APIEXT}.JSONSchemaPropsOrArray": {"description": "props or array"},
        f"{_APIEXT}.JSONSchemaPropsOrStringArray": {"description": "props or strings"},
        f"{_APIEXT}.JSONSchemaProps": {
            "type": "object",
            "properties": {
                "default": {"$ref": f"{ref}{_APIEXT}.JSON"},
                "enum": {"type": "array", "items": {"$ref": f"{ref}{_APIEXT}.JSON"}},
                "items": {"$ref": f"{ref}{_APIEXT}.JSONSchemaPropsOrArray"},
                "additionalProperties": {
                    "$ref": f"{ref}{_APIEXT}.JSONSchemaPropsOrBool"
                },
                "dependencies": {
                    "type": "object",
                    "additionalProperties": {
                        "$ref": f"{ref}{_APIEXT}.JSONSchemaPropsOrStringArray"
                    },
                },
            },
        },
        f"{_APIEXT}.CustomResourceValidation": {
            "type": "object",
            "properties": {
                "openAPIV3Schema": {"$ref": f"{ref}{_APIEXT}.JSONSchemaProps"}
            },
        },
        f"{_APIEXT}.CustomResourceDefinition": {
            "type": "object",
            "properties": {
                "apiVersion": {"type": "string"},
                "kind": {"type": "string"},
                "metadata": {"$ref": f"{ref}{_META}.ObjectMeta"},
                "validation": {"$ref": f"{ref}{_APIEXT}.CustomResourceValidation"},
            },
            "x-kubernetes-group-version-kind": [
                {
                    "group": "apiextensions.k8s.io",
                    "kind": "CustomResourceDefinition",
                    "version": "v1",
                }
            ],
        },
    }
    paths: dict[str, Any] = {
        "/apis/apiextensions.k8s.io/v1/customresourcedefinitions/{name}": {
            "get": {
                "x-kubernetes-group-version-kind": {
                    "group": "apiextensions.k8s.io",
                    "kind": "CustomResourceDefinition",
                    "version": "v1",
                }
            }
        }
    }
    build = _build(definitions, paths)
    prefix = "kubex.k8s.v1_30.apiextensions_k8s_io.v1"
    assert f"{prefix}.json_schema_props" in build.modules
    for gone in (
        "json",
        "json_schema_props_or_bool",
        "json_schema_props_or_array",
        "json_schema_props_or_string_array",
    ):
        assert f"{prefix}.{gone}" not in build.modules
    props = build.modules[f"{prefix}.json_schema_props"]
    by_alias = {f.alias: f.type_expression for f in props.classes[0].fields}
    assert by_alias == {
        "additionalProperties": "JSONSchemaProps | bool",
        "default": "Any",
        "dependencies": "dict[str, JSONSchemaProps | list[str]]",
        "enum": "list[Any]",
        "items": "JSONSchemaProps | list[JSONSchemaProps]",
    }
    # Self-referencing aliases need postponed annotations.
    assert props.imports.future_annotations is True


def test_build_modules_rejects_override_drift() -> None:
    definitions: dict[str, Any] = {
        f"{_META}.ObjectMeta": {
            "type": "object",
            "properties": {"name": {"type": "string"}, "brandNew": {"type": "string"}},
        }
    }
    with pytest.raises(OverrideDriftError, match="brandNew"):
        _build(definitions)
