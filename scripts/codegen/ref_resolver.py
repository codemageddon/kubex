"""Resolve swagger `$ref` definition names to (module, python_class) pairs.

Three categories of references:

1. **Overrides** — definitions whose spec exactly matches a hand-written
   `kubex_core` class; we import the existing class instead of emitting a copy.
   The override table is checked against the spec on every generation (see
   `validate_overrides`).
2. **Type aliases** — definitions that collapse to a Python type expression
   instead of a generated class (e.g. `IntOrString -> int | str`,
   `Quantity -> kubex_core Quantity`, `RawExtension -> dict[str, Any]`,
   `JSONSchemaPropsOrBool -> JSONSchemaProps | bool`). Definitions with no
   schema at all (no type, no properties) are aliased to `Any`.
3. **Generated** — everything else. We derive a `(group, version, class)`
   tuple from the dotted definition name, which maps to one Python module
   per (group, version).
"""

from __future__ import annotations

import importlib
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from scripts.codegen.naming import py_field_name

# Swagger definition name -> (python module, class name).
OVERRIDES: dict[str, tuple[str, str]] = {
    "io.k8s.apimachinery.pkg.apis.meta.v1.ObjectMeta": (
        "kubex_core.models.metadata",
        "ObjectMetadata",
    ),
    "io.k8s.apimachinery.pkg.apis.meta.v1.ListMeta": (
        "kubex_core.models.metadata",
        "ListMetadata",
    ),
    "io.k8s.apimachinery.pkg.apis.meta.v1.OwnerReference": (
        "kubex_core.models.metadata",
        "OwnerReference",
    ),
    "io.k8s.apimachinery.pkg.apis.meta.v1.ManagedFieldsEntry": (
        "kubex_core.models.metadata",
        "ManagedFieldsEntry",
    ),
    "io.k8s.apimachinery.pkg.apis.meta.v1.ShardInfo": (
        "kubex_core.models.metadata",
        "ShardInfo",
    ),
}


@dataclass(frozen=True)
class TypeAlias:
    """A definition that collapses to a Python type expression."""

    expression: str
    # `typing` symbols, or stdlib modules imported as `import <module>`.
    imports: tuple[tuple[str, str], ...] = ()
    # `from <module> import <symbol>` imports (e.g. kubex_core types).
    from_imports: tuple[tuple[str, str], ...] = ()
    # Generated definitions whose class names appear in `expression`; the
    # caller imports them when they live in another module.
    definition_refs: tuple[str, ...] = ()
    # The Go type marshals its zero value as JSON `null` (e.g. a zero
    # metav1.Time), so even a spec-required field can arrive as null.
    nullable: bool = False


_KUBEX_TYPES = "kubex_core.models.types"
_APIEXT_V1 = "io.k8s.apiextensions-apiserver.pkg.apis.apiextensions.v1"
_JSON_SCHEMA_PROPS = f"{_APIEXT_V1}.JSONSchemaProps"

TYPE_ALIASES: dict[str, TypeAlias] = {
    "io.k8s.apimachinery.pkg.util.intstr.IntOrString": TypeAlias(
        expression="int | str",
    ),
    "io.k8s.apimachinery.pkg.api.resource.Quantity": TypeAlias(
        expression="Quantity",
        from_imports=((_KUBEX_TYPES, "Quantity"),),
    ),
    "io.k8s.apimachinery.pkg.runtime.RawExtension": TypeAlias(
        expression="dict[str, Any]",
        imports=(("typing", "Any"),),
        nullable=True,
    ),
    "io.k8s.apimachinery.pkg.apis.meta.v1.Time": TypeAlias(
        expression="Time",
        from_imports=((_KUBEX_TYPES, "Time"),),
        nullable=True,
    ),
    "io.k8s.apimachinery.pkg.apis.meta.v1.MicroTime": TypeAlias(
        expression="MicroTime",
        from_imports=((_KUBEX_TYPES, "MicroTime"),),
        nullable=True,
    ),
    "io.k8s.apimachinery.pkg.apis.meta.v1.FieldsV1": TypeAlias(
        expression="dict[str, Any]",
        imports=(("typing", "Any"),),
        nullable=True,
    ),
    # apiextensions types with custom JSON (un)marshalling and no schema of
    # their own in the spec.
    f"{_APIEXT_V1}.JSON": TypeAlias(
        expression="Any",
        imports=(("typing", "Any"),),
    ),
    f"{_APIEXT_V1}.JSONSchemaPropsOrBool": TypeAlias(
        expression="JSONSchemaProps | bool",
        definition_refs=(_JSON_SCHEMA_PROPS,),
    ),
    f"{_APIEXT_V1}.JSONSchemaPropsOrArray": TypeAlias(
        expression="JSONSchemaProps | list[JSONSchemaProps]",
        definition_refs=(_JSON_SCHEMA_PROPS,),
    ),
    f"{_APIEXT_V1}.JSONSchemaPropsOrStringArray": TypeAlias(
        expression="JSONSchemaProps | list[str]",
        definition_refs=(_JSON_SCHEMA_PROPS,),
    ),
}

# Fallback for a definition that declares no schema at all: it can hold any
# JSON value, so an (empty) generated model would reject valid data.
OPAQUE_ALIAS = TypeAlias(expression="Any", imports=(("typing", "Any"),))

_SCHEMA_KEYS = frozenset(
    {
        "type",
        "properties",
        "additionalProperties",
        "items",
        "enum",
        "$ref",
        "allOf",
        "anyOf",
        "oneOf",
    }
)


def is_opaque_schema(schema: Mapping[str, Any] | None) -> bool:
    """True when a definition has no type, properties or composition keywords."""
    return schema is not None and not (_SCHEMA_KEYS & schema.keys())


@dataclass(frozen=True)
class Resolved:
    """Resolution result for a swagger `$ref` definition name."""

    module: str  # dotted Python module path, e.g. "kubex.k8s.v1_30.core_v1"
    class_name: str  # python class name
    is_override: bool = False
    is_alias: bool = False
    alias: TypeAlias | None = None


# Matches the standard Kubernetes API namespace:
#   io.k8s.api.<group>.<version>.<Class>
_API_RE = re.compile(
    r"^io\.k8s\.api\.(?P<group>[a-z0-9_\-]+)\.(?P<version>v[0-9a-z]+)\.(?P<cls>[A-Za-z0-9]+)$"
)
# apiextensions-apiserver and apimachinery have their own namespaces; the
# generator handles these via overrides/aliases, so everything left under the
# "io.k8s.apimachinery.*" or "io.k8s.apiextensions-apiserver.*" prefix that
# isn't matched above falls into `_APIEXTENSIONS_RE`.
_APIEXTENSIONS_RE = re.compile(
    r"^io\.k8s\.apiextensions-apiserver\.pkg\.apis\.apiextensions\.(?P<version>v[0-9a-z]+)\.(?P<cls>[A-Za-z0-9]+)$"
)
_KUBE_AGGREGATOR_RE = re.compile(
    r"^io\.k8s\.kube-aggregator\.pkg\.apis\.apiregistration\.(?P<version>v[0-9a-z]+)\.(?P<cls>[A-Za-z0-9]+)$"
)
_APIMACHINERY_META_RE = re.compile(
    r"^io\.k8s\.apimachinery\.pkg\.apis\.meta\.(?P<version>v[0-9a-z]+)\.(?P<cls>[A-Za-z0-9]+)$"
)


def module_for_definition(name: str, *, k8s_version_tag: str) -> tuple[str, str]:
    """Return `(module, class_name)` for a generated definition.

    `k8s_version_tag` is the version directory segment like `v1_30`.
    """
    base = f"kubex.k8s.{k8s_version_tag}"
    if m := _API_RE.match(name):
        group = m["group"]
        version = m["version"]
        cls = m["cls"]
        return (
            f"{base}.{_group_version_prefix(group, version)}.{py_field_name(cls)}",
            cls,
        )
    if m := _APIEXTENSIONS_RE.match(name):
        version = m["version"]
        cls = m["cls"]
        return f"{base}.apiextensions_k8s_io.{version}.{py_field_name(cls)}", cls
    if m := _KUBE_AGGREGATOR_RE.match(name):
        version = m["version"]
        cls = m["cls"]
        return f"{base}.apiregistration.{version}.{py_field_name(cls)}", cls
    if m := _APIMACHINERY_META_RE.match(name):
        version = m["version"]
        cls = m["cls"]
        return f"{base}.meta.{version}.{py_field_name(cls)}", cls
    raise ValueError(f"Cannot determine module for definition: {name!r}")


def _group_version_prefix(group: str, version: str) -> str:
    """`core` + `v1` -> `core.v1`; handles dots in group names."""
    return f"{group.replace('.', '_').replace('-', '_')}.{version}"


def resolve(
    name: str,
    *,
    k8s_version_tag: str,
    definitions: Mapping[str, Mapping[str, Any]] | None = None,
) -> Resolved:
    """Resolve a swagger definition name.

    With `definitions`, a definition that has no schema of its own resolves to
    `Any` (see `is_opaque_schema`).
    """
    if name in OVERRIDES:
        module, cls = OVERRIDES[name]
        return Resolved(module=module, class_name=cls, is_override=True)
    alias = TYPE_ALIASES.get(name)
    if alias is None and definitions is not None:
        if is_opaque_schema(definitions.get(name)):
            alias = OPAQUE_ALIAS
    if alias is not None:
        return Resolved(
            module="",
            class_name="",
            is_alias=True,
            alias=alias,
        )
    module, cls = module_for_definition(name, k8s_version_tag=k8s_version_tag)
    return Resolved(module=module, class_name=cls)


class OverrideDriftError(ValueError):
    """A hand-written kubex_core override lacks properties the spec defines."""


def collect_override_field_sets() -> dict[str, set[str]]:
    """Wire (alias) names of the fields each kubex_core override declares."""
    out: dict[str, set[str]] = {}
    for name, (module, cls_name) in OVERRIDES.items():
        cls = getattr(importlib.import_module(module), cls_name)
        out[name] = {
            info.alias or field_name for field_name, info in cls.model_fields.items()
        }
    return out


def validate_overrides(
    definitions: Mapping[str, Mapping[str, Any]],
    *,
    override_field_sets: Mapping[str, set[str]] | None = None,
) -> None:
    """Fail fast if a hand-written override has drifted from the OpenAPI spec.

    `override_field_sets[name]` is the set of aliases (i.e. JSON property names)
    that the kubex_core class declares; by default it is read from the
    classes themselves. Only property names are compared, not types, since
    the override classes intentionally loosen some types (optional vs
    required). Unknown fields still round-trip through `extra="allow"`, but
    they would be untyped, so a spec property missing from an override is an
    error: add it to the kubex_core class.
    """
    if override_field_sets is None:
        override_field_sets = collect_override_field_sets()
    problems: list[str] = []
    for name in OVERRIDES:
        if name not in definitions:
            # Spec removed it; an overlay issue but not fatal.
            continue
        spec_properties = set((definitions[name].get("properties") or {}).keys())
        local = override_field_sets.get(name)
        if local is None:
            continue
        missing = spec_properties - local
        if missing:
            module, cls = OVERRIDES[name]
            problems.append(f"{name} -> {module}.{cls}: {sorted(missing)}")
    if problems:
        raise OverrideDriftError(
            "Override drift: spec properties not declared on the kubex_core "
            "override class:\n  " + "\n  ".join(problems)
        )
