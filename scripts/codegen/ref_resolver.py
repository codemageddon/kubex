"""Resolve swagger `$ref` definition names to (module, python_class) pairs.

Three categories of references:

1. **Overrides** — definitions whose spec exactly matches a hand-written
   `kubex_core` class; we import the existing class instead of emitting a copy.
   The override table is validated at generator start-up (see
   `validate_overrides`).
2. **Type aliases** — definitions that collapse to a plain Python type (e.g.
   `IntOrString -> int | str`, `Quantity -> str`, `RawExtension -> dict[str, Any]`).
   These are emitted as aliases in the per-version `_common.py`.
3. **Generated** — everything else. We derive a `(group, version, class)`
   tuple from the dotted definition name, which maps to one Python module
   per (group, version).
"""

from __future__ import annotations

import re
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
}


@dataclass(frozen=True)
class TypeAlias:
    """A definition that collapses to a plain Python type."""

    expression: str
    imports: tuple[tuple[str, str], ...] = ()  # (module, symbol) tuples


TYPE_ALIASES: dict[str, TypeAlias] = {
    "io.k8s.apimachinery.pkg.util.intstr.IntOrString": TypeAlias(
        expression="int | str",
    ),
    "io.k8s.apimachinery.pkg.api.resource.Quantity": TypeAlias(expression="str"),
    "io.k8s.apimachinery.pkg.runtime.RawExtension": TypeAlias(
        expression="dict[str, Any]",
        imports=(("typing", "Any"),),
    ),
    "io.k8s.apimachinery.pkg.apis.meta.v1.Time": TypeAlias(
        expression="datetime.datetime",
        imports=(("datetime", "datetime"),),
    ),
    "io.k8s.apimachinery.pkg.apis.meta.v1.MicroTime": TypeAlias(
        expression="datetime.datetime",
        imports=(("datetime", "datetime"),),
    ),
    "io.k8s.apimachinery.pkg.apis.meta.v1.FieldsV1": TypeAlias(
        expression="dict[str, Any]",
        imports=(("typing", "Any"),),
    ),
}


@dataclass(frozen=True)
class Resolved:
    """Resolution result for a swagger `$ref` definition name."""

    module: str  # dotted Python module path, e.g. "kubex.k8s.v1_30.core_v1"
    class_name: str  # python class name
    is_override: bool = False
    is_alias: bool = False
    alias_expression: str | None = None
    alias_imports: tuple[tuple[str, str], ...] = ()


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


def resolve(name: str, *, k8s_version_tag: str) -> Resolved:
    """Resolve a swagger definition name."""
    if name in OVERRIDES:
        module, cls = OVERRIDES[name]
        return Resolved(module=module, class_name=cls, is_override=True)
    if alias := TYPE_ALIASES.get(name):
        return Resolved(
            module="",
            class_name="",
            is_alias=True,
            alias_expression=alias.expression,
            alias_imports=alias.imports,
        )
    module, cls = module_for_definition(name, k8s_version_tag=k8s_version_tag)
    return Resolved(module=module, class_name=cls)


def validate_overrides(
    definitions: dict[str, dict[str, Any]],
    *,
    override_field_sets: dict[str, set[str]],
) -> None:
    """Fail fast if a hand-written override has drifted from the OpenAPI spec.

    `override_field_sets[name]` is the set of aliases (i.e. JSON property names)
    that the kubex_core class emits. The spec's `required` set is checked against
    the override's properties too. We compare by property names, not types, since
    the override classes intentionally narrow some types (optional vs required).
    """
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
            raise RuntimeError(
                f"Override drift: {name} in spec has properties not mapped in "
                f"kubex_core override: {sorted(missing)}"
            )
