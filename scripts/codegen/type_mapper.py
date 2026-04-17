"""JSON schema -> Python type expression.

Each resolution returns:
- the Python type expression (as a string) to drop into the generated field
- a set of imports to add to the module header
- zero or more generated enum requests that the caller should register with
  `enum_emitter`
- zero or more cross-module class references the caller should add to the
  module's import list
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from scripts.codegen import ref_resolver
from scripts.codegen.naming import class_name_for_enum


@dataclass
class EnumRequest:
    """Pending enum generation triggered by a schema node with `enum`."""

    class_name: str  # final PascalCase enum class name
    values: tuple[str, ...]
    owner_definition_short: str  # e.g. "Pod" for io.k8s.api.core.v1.Pod
    owner_module: str  # e.g. "kubex.k8s.v1_30.core_v1"


@dataclass
class CrossRef:
    """A reference to a class defined in another module (needs an `import`)."""

    module: str
    class_name: str


@dataclass
class MappedType:
    """Outcome of `map_type`."""

    expression: str
    typing_imports: set[str] = field(default_factory=set)  # names from `typing`
    stdlib_imports: set[tuple[str, str]] = field(
        default_factory=set
    )  # (module, symbol)
    cross_refs: list[CrossRef] = field(default_factory=list)
    enum_requests: list[EnumRequest] = field(default_factory=list)


def map_type(
    schema: dict[str, Any],
    *,
    k8s_version_tag: str,
    owner_definition: str,
    owner_module: str,
    property_name: str,
) -> MappedType:
    """Translate a single schema node to a Python type expression.

    `owner_definition` is the full dotted swagger name of the definition that
    owns this property (used to derive enum class names). `owner_module` is the
    generated Python module that definition lands in (used to decide whether an
    enum goes inline or cross-module-shared).
    """
    out = MappedType(expression="Any")
    out.typing_imports.add("Any")  # default; overwritten below when we resolve

    # 1) $ref -> delegate to resolver.
    ref = schema.get("$ref")
    if isinstance(ref, str):
        return _map_ref(ref, k8s_version_tag=k8s_version_tag, owner_module=owner_module)

    # 2) enum -> generate an Enum class.
    values = schema.get("enum")
    if isinstance(values, list) and values and all(isinstance(v, str) for v in values):
        short = _short_name(owner_definition)
        cls = class_name_for_enum(short, property_name)
        out = MappedType(expression=cls)
        out.enum_requests.append(
            EnumRequest(
                class_name=cls,
                values=tuple(values),
                owner_definition_short=short,
                owner_module=owner_module,
            )
        )
        return out

    t = schema.get("type")
    fmt = schema.get("format")

    # 3) arrays.
    if t == "array":
        items = schema.get("items") or {}
        inner = map_type(
            items,
            k8s_version_tag=k8s_version_tag,
            owner_definition=owner_definition,
            owner_module=owner_module,
            property_name=property_name,
        )
        merged = _merge(inner)
        merged.expression = f"list[{inner.expression}]"
        return merged

    # 4) object with additionalProperties -> dict[str, V].
    if t == "object":
        ap = schema.get("additionalProperties")
        if isinstance(ap, dict):
            inner = map_type(
                ap,
                k8s_version_tag=k8s_version_tag,
                owner_definition=owner_definition,
                owner_module=owner_module,
                property_name=property_name,
            )
            merged = _merge(inner)
            merged.expression = f"dict[str, {inner.expression}]"
            return merged
        # free-form object -> dict[str, Any]
        return MappedType(expression="dict[str, Any]", typing_imports={"Any"})

    # 5) primitives.
    if t == "string":
        if fmt == "date-time":
            return MappedType(
                expression="datetime.datetime",
                stdlib_imports={("datetime", "datetime")},
            )
        if fmt == "byte":
            return MappedType(expression="str")
        if fmt == "int-or-string":
            return MappedType(
                expression="IntOrString",
                cross_refs=[
                    CrossRef(
                        module=f"kubex.k8s.{k8s_version_tag}._common",
                        class_name="IntOrString",
                    )
                ],
            )
        return MappedType(expression="str")
    if t == "integer":
        return MappedType(expression="int")
    if t == "number":
        return MappedType(expression="float")
    if t == "boolean":
        return MappedType(expression="bool")

    # 6) fallback for ambiguous / union schemas we don't handle yet.
    return MappedType(
        expression="Any  # TODO: unhandled schema", typing_imports={"Any"}
    )


def _map_ref(ref: str, *, k8s_version_tag: str, owner_module: str) -> MappedType:
    if not ref.startswith("#/definitions/"):
        return MappedType(
            expression="Any  # TODO: non-local $ref", typing_imports={"Any"}
        )
    name = ref.removeprefix("#/definitions/")
    resolved = ref_resolver.resolve(name, k8s_version_tag=k8s_version_tag)
    if resolved.is_alias:
        assert resolved.alias_expression is not None
        out = MappedType(expression=resolved.alias_expression)
        for mod, sym in resolved.alias_imports:
            if mod == "typing":
                out.typing_imports.add(sym)
            else:
                out.stdlib_imports.add((mod, sym))
        return out
    # Class lives in some module — same or cross.
    if resolved.module == owner_module:
        return MappedType(expression=resolved.class_name)
    return MappedType(
        expression=resolved.class_name,
        cross_refs=[CrossRef(module=resolved.module, class_name=resolved.class_name)],
    )


def _merge(inner: MappedType) -> MappedType:
    """Shallow copy so wrappers (list[], dict[str,]) can overwrite `.expression`."""
    return MappedType(
        expression=inner.expression,
        typing_imports=set(inner.typing_imports),
        stdlib_imports=set(inner.stdlib_imports),
        cross_refs=list(inner.cross_refs),
        enum_requests=list(inner.enum_requests),
    )


def _short_name(definition: str) -> str:
    """`io.k8s.api.core.v1.Pod` -> `Pod`."""
    return definition.rsplit(".", 1)[-1]
