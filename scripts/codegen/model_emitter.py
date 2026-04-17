"""Emit one Python module per (group, version) from OpenAPI definitions.

This module orchestrates:
- walking the definitions belonging to a module,
- calling `type_mapper` to produce a type expression per property,
- accumulating enum requests and cross-module imports,
- topologically sorting classes so ordinary (non-string) annotations work,
- and rendering the module through Jinja.

Resources (carrying `x-kubernetes-group-version-kind`) are emitted with the
right marker-interface inheritance + `__RESOURCE_CONFIG__`. Their paired
`*List` classes are also emitted explicitly and wired via a trailing
`X.__RESOURCE_CONFIG__._list_model = XList` statement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from scripts.codegen import enum_emitter, ref_resolver
from scripts.codegen.naming import py_field_name
from scripts.codegen.resource_detector import ResourceInfo
from scripts.codegen.type_mapper import MappedType, map_type

# ---------------------------------------------------------------------------
# Intermediate representation types.
# ---------------------------------------------------------------------------


@dataclass
class EmittedField:
    """One property on a generated class."""

    python_name: str
    alias: str
    type_expression: str
    required: bool
    description: str | None
    default_expression: str | None = (
        None  # overrides `default=None` when set (e.g. Literal defaults)
    )


@dataclass
class EmittedClass:
    """A Pydantic class to render in a module."""

    class_name: str
    bases: list[str]
    docstring: str | None
    fields: list[EmittedField]
    # References to same-module classes used by this class's fields — edges in
    # the topological sort graph.
    local_refs: set[str] = field(default_factory=set)
    # A resource class gets a `__RESOURCE_CONFIG__` literal.
    resource_info: ResourceInfo | None = None
    # A list class is wired via a trailing assignment — we carry the single
    # owner so the emitter can write `Owner.__RESOURCE_CONFIG__._list_model = ClsName`.
    list_owner_class: str | None = None


@dataclass
class EmittedModule:
    """All state needed to render one `core_v1.py`-shaped file."""

    module_path: str  # dotted: "kubex.k8s.v1_30.core_v1"
    file_name: str  # "core_v1.py"
    classes: list[EmittedClass] = field(default_factory=list)
    enums: list[enum_emitter.EmittedEnum] = field(default_factory=list)
    imports: "ImportSet" = field(default_factory=lambda: ImportSet())
    trailing_assignments: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Import tracking.
# ---------------------------------------------------------------------------


class ImportSet:
    """Collects `import ...` / `from X import Y` entries for a module."""

    def __init__(self) -> None:
        self._stdlib: set[tuple[str, str]] = set()  # (module, symbol)
        self._typing: set[str] = set()
        self._from: dict[str, set[str]] = {}  # module -> set of symbols
        self._raw_modules: set[str] = set()  # `import X`

    def add_stdlib(self, module: str, symbol: str) -> None:
        self._stdlib.add((module, symbol))

    def add_typing(self, symbol: str) -> None:
        self._typing.add(symbol)

    def add_from(self, module: str, symbol: str) -> None:
        self._from.setdefault(module, set()).add(symbol)

    def add_import(self, module: str) -> None:
        self._raw_modules.add(module)

    def render(self) -> str:
        blocks: list[str] = []
        # 1) `import X`  (datetime etc. come in here via stdlib_imports too — normalized)
        raw_modules = sorted(self._raw_modules | {m for m, _ in self._stdlib})
        if raw_modules:
            blocks.append("\n".join(f"import {m}" for m in raw_modules))
        # 2) typing imports collapsed onto one line.
        if self._typing:
            typing_line = "from typing import " + ", ".join(sorted(self._typing))
            blocks.append(typing_line)
        # 3) grouped `from X import Y` — pydantic, enum, kubex_core, kubex.k8s.
        ordered_from = sorted(self._from.items())
        if ordered_from:
            lines = []
            for module, symbols in ordered_from:
                syms = ", ".join(sorted(symbols))
                lines.append(f"from {module} import {syms}")
            blocks.append("\n".join(lines))
        return "\n\n".join(b for b in blocks if b)


# ---------------------------------------------------------------------------
# Entrypoint: build modules from a spec.
# ---------------------------------------------------------------------------


@dataclass
class EmissionContext:
    """Inputs and outputs shared across the emission pass."""

    k8s_version_tag: str  # "v1_30"
    definitions: dict[str, dict[str, Any]]
    resources_by_def: dict[str, ResourceInfo]
    pending_enum_requests: list[Any] = field(default_factory=list)


@dataclass
class BuildResult:
    """Output of `build_modules`: the per-group modules plus any shared enums."""

    modules: dict[str, EmittedModule]
    shared_enums: list[enum_emitter.EmittedEnum]


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
    # Resource definitions (and their paired *List) emit into a specific group
    # module. All other referenced definitions tag along into the same module
    # via $ref resolution.
    for defn in _reachable_definitions(ctx):
        resolved = ref_resolver.resolve(defn, k8s_version_tag=k8s_version_tag)
        if resolved.is_override or resolved.is_alias:
            continue
        module_path = resolved.module
        module = modules.setdefault(
            module_path,
            EmittedModule(
                module_path=module_path,
                file_name=module_path.rsplit(".", 1)[-1] + ".py",
            ),
        )
        emitted = _emit_definition(
            defn,
            ctx=ctx,
            module_path=module_path,
            module=module,
        )
        module.classes.append(emitted)

    # 2) Plan enums across modules.
    enum_plan = enum_emitter.plan_enums(
        ctx.pending_enum_requests,
        common_module=f"kubex.k8s.{k8s_version_tag}._common",
    )

    # Swap in final (potentially renamed) enum class names in field expressions.
    _rewrite_enum_references(modules, enum_plan)

    # Distribute enums and wire imports.
    for module_path, module in modules.items():
        module.enums = enum_plan.by_module.get(module_path, [])
        if module.enums:
            module.imports.add_from("enum", "Enum")
    # Cross-module enum imports: any enum referenced in module M but defined in
    # common -> add `from <common> import <Name>`.
    for module_path, module in modules.items():
        for cls in module.classes:
            for field_ in cls.fields:
                # Nothing to do — cross-module class imports were added during
                # _emit_definition via `module.imports.add_from`. Enum cross-module
                # imports are wired below by inspecting usage vs plan.
                pass
    _wire_cross_module_enum_imports(modules, enum_plan)

    # 3) Topologically sort each module.
    for module in modules.values():
        module.classes = _topo_sort(module.classes)
        # Always-needed imports.
        module.imports.add_from("pydantic", "Field")
        module.imports.add_from("kubex_core.models.base", "BaseK8sModel")

    # 4) Emit trailing list wire statements (only in modules that have a
    #    resource+list pair).
    for module in modules.values():
        _emit_list_wire_assignments(module)

    common_module = f"kubex.k8s.{k8s_version_tag}._common"
    shared = enum_plan.by_module.get(common_module, [])
    return BuildResult(modules=modules, shared_enums=shared)


# ---------------------------------------------------------------------------
# Per-definition emission.
# ---------------------------------------------------------------------------


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
    local_refs: set[str] = set()

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
        local_refs |= mapped.local_refs
        ctx.pending_enum_requests.extend(mapped.enum_requests)

        # Specialize api_version / kind with Literal for resource + list classes.
        # These are always treated as required (a K8s object always has a kind/apiVersion),
        # and we emit the concrete literal as the Field default so the pydantic model
        # needs no `kind="Pod"` at construction time.
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
            # Paired *List models always carry metadata+items; `ListEntity` base
            # declares them required so we surface them as required here too,
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
        local_refs=local_refs,
        resource_info=res_info if is_resource else None,
        list_owner_class=_list_owner_name(defn, ctx) if is_list else None,
    )


# ---------------------------------------------------------------------------
# Helpers: reachable definitions, inheritance, imports.
# ---------------------------------------------------------------------------


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
    # list_defn: "io.k8s.api.core.v1.PodList"
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


def _topo_sort(classes: list[EmittedClass]) -> list[EmittedClass]:
    """Stable topological sort: classes without dependencies first, alphabetical within a layer."""
    by_name = {c.class_name: c for c in classes}
    in_degree = {c.class_name: 0 for c in classes}
    deps: dict[str, set[str]] = {c.class_name: set() for c in classes}
    for c in classes:
        for ref in c.local_refs:
            if ref in by_name and ref != c.class_name:
                deps[c.class_name].add(ref)
    for name, d in deps.items():
        in_degree[name] = len(d)

    ready = sorted([n for n, deg in in_degree.items() if deg == 0])
    ordered: list[EmittedClass] = []
    removed: set[str] = set()
    while ready:
        name = ready.pop(0)
        ordered.append(by_name[name])
        removed.add(name)
        next_ready: list[str] = []
        for other, d in deps.items():
            if other in removed:
                continue
            if name in d:
                d.discard(name)
                if not d:
                    next_ready.append(other)
        ready = sorted(ready + next_ready)

    if len(ordered) != len(classes):
        remaining = [c.class_name for c in classes if c.class_name not in removed]
        raise RuntimeError(f"Cycle detected among generated classes: {remaining}")
    return ordered


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


def _clean_doc(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    # Collapse to single line; many K8s descriptions have embedded newlines and
    # backslashes that confuse docstrings.
    return " ".join(value.split())
