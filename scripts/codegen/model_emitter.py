"""Emit one Python module per definition from OpenAPI definitions.

This module orchestrates:
- walking the definitions belonging to a module,
- calling `type_mapper` to produce a type expression per property,
- accumulating enum requests and cross-module imports.

Resources (carrying `x-kubernetes-group-version-kind`) are emitted with the
right marker-interface inheritance + `__RESOURCE_CONFIG__`. Their paired
`*List` classes are also emitted explicitly and wired via a trailing
`X.__RESOURCE_CONFIG__._list_model = XList` statement.

IR types live in `ir.py`; the import accumulator lives in `imports.py`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from scripts.codegen import enum_emitter, ref_resolver
from scripts.codegen.ir import (
    BuildResult,
    EmittedClass,
    EmittedField,
    EmittedModule,
)
from scripts.codegen.naming import py_field_name
from scripts.codegen.resource_detector import ResourceInfo
from scripts.codegen.type_mapper import MappedType, map_type


@dataclass
class EmissionContext:
    """Inputs and outputs shared across the emission pass."""

    k8s_version_tag: str  # "v1_30"
    definitions: dict[str, dict[str, Any]]
    resources_by_def: dict[str, ResourceInfo]
    pending_enum_requests: list[Any] = field(default_factory=list)


def build_modules(
    *,
    k8s_version_tag: str,
    definitions: dict[str, dict[str, Any]],
    resources: list[ResourceInfo],
) -> BuildResult:
    """Build a `{module_path: EmittedModule}` map plus the `_common.py` enums."""
    ctx = EmissionContext(
        k8s_version_tag=k8s_version_tag,
        definitions=definitions,
        resources_by_def={r.definition: r for r in resources},
    )

    modules: dict[str, EmittedModule] = {}
    for defn in _reachable_definitions(ctx):
        resolved = ref_resolver.resolve(defn, k8s_version_tag=k8s_version_tag)
        if resolved.is_override or resolved.is_alias:
            continue
        module_path = resolved.module
        module = EmittedModule(
            module_path=module_path,
            file_name=module_path.rsplit(".", 1)[-1] + ".py",
        )
        emitted = _emit_definition(
            defn,
            ctx=ctx,
            module_path=module_path,
            module=module,
        )
        module.classes.append(emitted)
        # Detect self-referential types: if any field's type expression
        # references the class being defined, we need `from __future__ import
        # annotations` so the forward reference is valid at runtime.
        if _class_has_self_reference(emitted):
            module.imports.future_annotations = True
        modules[module_path] = module

    enum_plan = enum_emitter.plan_enums(
        ctx.pending_enum_requests,
        common_module=f"kubex.k8s.{k8s_version_tag}._common",
    )
    _rewrite_enum_references(modules, enum_plan)

    # Create EmittedModule entries for _enums.py modules that don't exist yet
    for enum_module_path in enum_plan.by_module:
        if (
            enum_module_path not in modules
            and enum_module_path != f"kubex.k8s.{k8s_version_tag}._common"
        ):
            modules[enum_module_path] = EmittedModule(
                module_path=enum_module_path,
                file_name="_enums.py",
            )

    for module_path, module in modules.items():
        module.enums = enum_plan.by_module.get(module_path, [])
        if module.enums:
            module.imports.add_from("enum", "Enum")
    _wire_cross_module_enum_imports(modules, enum_plan)

    for module in modules.values():
        if any(cls.fields for cls in module.classes):
            module.imports.add_from("pydantic", "Field")

    for module in modules.values():
        _emit_list_wire_assignments(module)

    common_module = f"kubex.k8s.{k8s_version_tag}._common"
    shared = enum_plan.by_module.get(common_module, [])
    return BuildResult(modules=modules, shared_enums=shared)


def _emit_definition(
    defn: str,
    *,
    ctx: EmissionContext,
    module_path: str,
    module: EmittedModule,
) -> EmittedClass:
    schema = ctx.definitions[defn]
    short = defn.rsplit(".", 1)[-1]
    description = _clean_doc(schema.get("description"))
    properties = schema.get("properties") or {}
    required = set(schema.get("required") or [])

    is_resource = defn in ctx.resources_by_def
    res_info = ctx.resources_by_def.get(defn)
    is_list = (
        res_info is None and short.endswith("List") and _is_list_schema(properties)
    )

    fields: list[EmittedField] = []

    # For resource classes, `metadata` is inherited from BaseEntity; skip.
    # For list classes, we redeclare metadata/items explicitly since they use
    # ListMetadata and a typed items list.
    skip = {"metadata"} if is_resource else set()

    for prop_name in sorted(properties.keys()):
        if prop_name in skip:
            continue
        prop_schema = properties[prop_name]
        mapped = map_type(
            prop_schema,
            k8s_version_tag=ctx.k8s_version_tag,
            owner_definition=defn,
            owner_module=module_path,
            property_name=prop_name,
        )
        _merge_imports(module, mapped)
        ctx.pending_enum_requests.extend(mapped.enum_requests)

        # api_version / kind on a resource or list carry a concrete Literal
        # default so the constructor doesn't need `kind="Pod"` spelled out.
        type_expr = mapped.expression
        default_expr: str | None = None
        force_required = False
        if is_resource and res_info is not None and prop_name in ("apiVersion", "kind"):
            literal_value = (
                _api_version_literal(res_info)
                if prop_name == "apiVersion"
                else res_info.kind
            )
            type_expr = f'Literal["{literal_value}"]'
            default_expr = f'default="{literal_value}"'
            force_required = True
            module.imports.add_typing("Literal")
        if is_list and prop_name in ("apiVersion", "kind"):
            if prop_name == "apiVersion":
                owner = _list_owner_info(defn, ctx)
                if owner is not None:
                    literal_value = _api_version_literal(owner)
                    type_expr = f'Literal["{literal_value}"]'
                    default_expr = f'default="{literal_value}"'
                    force_required = True
                    module.imports.add_typing("Literal")
            else:
                type_expr = f'Literal["{short}"]'
                default_expr = f'default="{short}"'
                force_required = True
                module.imports.add_typing("Literal")
        if is_list and prop_name in ("metadata", "items"):
            # ListEntity base declares these required; surface them required here
            # even when the schema omits them from `required`.
            force_required = True

        py_name = py_field_name(prop_name)
        is_required = prop_name in required or force_required
        fields.append(
            EmittedField(
                python_name=py_name,
                alias=prop_name,
                type_expression=type_expr,
                required=is_required,
                description=_clean_doc(prop_schema.get("description")),
                default_expression=default_expr,
            )
        )

    bases = _bases_for(defn, ctx, is_list=is_list)
    for base in bases:
        _import_base(module, base, ctx)

    return EmittedClass(
        class_name=short,
        bases=bases,
        docstring=description,
        fields=fields,
        resource_info=res_info if is_resource else None,
        list_owner_class=_list_owner_name(defn, ctx) if is_list else None,
    )


def _reachable_definitions(ctx: EmissionContext) -> list[str]:
    """Return all definitions reachable from resource definitions via `$ref`.

    We only emit what's reachable from a known resource (plus its paired *List)
    so the generated package doesn't pull in random server-internal types.
    """
    seen: set[str] = set()
    queue: list[str] = []
    for info in ctx.resources_by_def.values():
        queue.append(info.definition)
        if info.list_definition is not None:
            queue.append(info.list_definition)
    while queue:
        name = queue.pop()
        if name in seen or name not in ctx.definitions:
            continue
        seen.add(name)
        for ref in _iter_refs(ctx.definitions[name]):
            target = ref.removeprefix("#/definitions/")
            if target not in seen:
                queue.append(target)
    return sorted(seen)


def _iter_refs(schema: Any) -> list[str]:
    out: list[str] = []
    if isinstance(schema, dict):
        ref = schema.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/definitions/"):
            out.append(ref)
        for v in schema.values():
            out.extend(_iter_refs(v))
    elif isinstance(schema, list):
        for v in schema:
            out.extend(_iter_refs(v))
    return out


def _bases_for(defn: str, ctx: EmissionContext, *, is_list: bool) -> list[str]:
    if is_list:
        owner = _list_owner_info(defn, ctx)
        if owner is None:
            return ["BaseK8sModel"]
        return [f"ListEntity[{owner.kind}]"]
    info = ctx.resources_by_def.get(defn)
    if info is None:
        return ["BaseK8sModel"]
    bases: list[str] = []
    bases.append(
        "NamespaceScopedEntity" if info.is_namespaced else "ClusterScopedEntity"
    )
    if info.has_logs:
        bases.append("HasLogs")
    if info.is_evictable:
        bases.append("Evictable")
    if info.has_scale:
        bases.append("HasScaleSubresource")
    if info.has_status:
        bases.append("HasStatusSubresource")
    return bases


def _import_base(module: EmittedModule, base: str, ctx: EmissionContext) -> None:
    if base == "BaseK8sModel":
        module.imports.add_from("kubex_core.models.base", "BaseK8sModel")
    elif base.startswith("ListEntity["):
        module.imports.add_from("kubex_core.models.list_entity", "ListEntity")
        module.imports.add_from("kubex_core.models.metadata", "ListMetadata")
    elif base in {
        "NamespaceScopedEntity",
        "ClusterScopedEntity",
        "HasLogs",
        "HasStatusSubresource",
        "HasScaleSubresource",
        "Evictable",
    }:
        module.imports.add_from("kubex_core.models.interfaces", base)
        module.imports.add_from("kubex_core.models.resource_config", "ResourceConfig")
        module.imports.add_from("kubex_core.models.resource_config", "Scope")
        module.imports.add_typing("ClassVar")


def _is_list_schema(properties: dict[str, Any]) -> bool:
    """Heuristic: list classes have `items` + `metadata` + `kind` + `apiVersion`."""
    return {"items", "metadata", "kind", "apiVersion"}.issubset(properties.keys())


def _list_owner_info(list_defn: str, ctx: EmissionContext) -> ResourceInfo | None:
    """Given a list definition, return the matching single-entity resource info."""
    if not list_defn.endswith("List"):
        return None
    owner_def = list_defn[: -len("List")]
    return ctx.resources_by_def.get(owner_def)


def _list_owner_name(list_defn: str, ctx: EmissionContext) -> str | None:
    info = _list_owner_info(list_defn, ctx)
    return info.kind if info else None


def _api_version_literal(info: ResourceInfo) -> str:
    if info.group and info.group != "core":
        return f"{info.group}/{info.version}"
    return info.version


def _merge_imports(module: EmittedModule, mapped: MappedType) -> None:
    for sym in mapped.typing_imports:
        module.imports.add_typing(sym)
    for stdlib_mod, stdlib_sym in mapped.stdlib_imports:
        module.imports.add_stdlib(stdlib_mod, stdlib_sym)
    for xref in mapped.cross_refs:
        module.imports.add_from(xref.module, xref.class_name)


def _emit_list_wire_assignments(module: EmittedModule) -> None:
    for cls in module.classes:
        if cls.list_owner_class is not None:
            module.trailing_assignments.append(
                f"{cls.list_owner_class}.__RESOURCE_CONFIG__._list_model = {cls.class_name}"
            )


def _rewrite_enum_references(
    modules: dict[str, EmittedModule],
    plan: enum_emitter.EnumPlan,
) -> None:
    """After planning, swap placeholder enum class names in field expressions."""
    for module_path, module in modules.items():
        for cls in module.classes:
            for field_ in cls.fields:
                for (orig_name, orig_module), (
                    final_name,
                    _final_target,
                ) in plan.request_index.items():
                    if orig_module != module_path:
                        continue
                    if orig_name == final_name:
                        continue
                    field_.type_expression = field_.type_expression.replace(
                        orig_name, final_name
                    )


def _wire_cross_module_enum_imports(
    modules: dict[str, EmittedModule],
    plan: enum_emitter.EnumPlan,
) -> None:
    for (_, orig_module), (final_name, target_module) in plan.request_index.items():
        module = modules.get(orig_module)
        if module is None or target_module == orig_module:
            continue
        module.imports.add_from(target_module, final_name)


def _class_has_self_reference(cls: EmittedClass) -> bool:
    """Return True if any field type expression references the class itself."""
    import re

    name = cls.class_name
    # Match the class name as a whole word (not as part of a longer name).
    pattern = re.compile(rf"\b{re.escape(name)}\b")
    return any(pattern.search(f.type_expression) for f in cls.fields)


def _clean_doc(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    # Collapse to single line; K8s descriptions contain embedded newlines and
    # backslashes that confuse docstrings.
    return " ".join(value.split())
