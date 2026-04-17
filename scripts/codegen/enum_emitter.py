"""Collect enum requests emitted during type mapping and decide where to place them.

Placement rule:
- enum referenced by exactly one target module -> emit inline in that module
- enum referenced by 2+ modules -> emit once in `_common.py`, imported elsewhere

Dedupe rule: if two requests share a class name **and** an identical ordered
value tuple, they collapse into one emitted class. If the class names match but
the values differ, the later request is disambiguated by appending the owning
definition's short name.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from scripts.codegen.naming import screaming_snake
from scripts.codegen.type_mapper import EnumRequest


@dataclass
class EmittedEnum:
    """A concrete enum class that will be written to disk."""

    class_name: str
    values: tuple[str, ...]
    target_module: str  # dotted module path where the Enum will be defined


@dataclass
class EnumPlan:
    """Final plan for every enum in the generated package."""

    by_module: dict[str, list[EmittedEnum]] = field(default_factory=dict)
    # Maps the original (class_name, owner_module) request key to the emitted
    # class's final (class_name, target_module).
    request_index: dict[tuple[str, str], tuple[str, str]] = field(default_factory=dict)


def _group_enums_module(modules: set[str]) -> str | None:
    """If all modules share a group/version prefix, return the `_enums` module path.

    E.g., given `{"kubex.k8s.v1_30.core.v1.pod", "kubex.k8s.v1_30.core.v1.service"}`,
    returns `"kubex.k8s.v1_30.core.v1._enums"`.
    Returns `None` if modules span different groups/versions.
    """
    prefixes = {mod.rsplit(".", 1)[0] for mod in modules}
    if len(prefixes) == 1:
        return f"{next(iter(prefixes))}._enums"
    return None


def plan_enums(requests: list[EnumRequest], *, common_module: str) -> EnumPlan:
    """Resolve a flat list of enum requests into an emission plan."""
    # Group requests by (class_name, values); conflicting-value requests that
    # share a class name get a disambiguating suffix.
    grouped: dict[tuple[str, tuple[str, ...]], list[EnumRequest]] = {}
    for req in requests:
        grouped.setdefault((req.class_name, req.values), []).append(req)

    # Detect class_name collisions where values differ; rename later requests.
    seen_names: dict[str, tuple[str, ...]] = {}
    renames: dict[tuple[str, tuple[str, ...]], str] = {}
    for (name, values), reqs in list(grouped.items()):
        if name in seen_names and seen_names[name] != values:
            disambig = f"{name}{reqs[0].owner_definition_short}"
            renames[(name, values)] = disambig
        else:
            seen_names[name] = values

    plan = EnumPlan()
    for (name, values), reqs in grouped.items():
        final_name = renames.get((name, values), name)
        target_modules = {r.owner_module for r in reqs}
        if len(target_modules) == 1:
            target_module = next(iter(target_modules))
        else:
            group_module = _group_enums_module(target_modules)
            target_module = group_module if group_module is not None else common_module
        plan.by_module.setdefault(target_module, []).append(
            EmittedEnum(
                class_name=final_name, values=values, target_module=target_module
            )
        )
        for req in reqs:
            plan.request_index[(req.class_name, req.owner_module)] = (
                final_name,
                target_module,
            )

    # Stable ordering per module.
    for mod in plan.by_module:
        plan.by_module[mod].sort(key=lambda e: e.class_name)
    return plan


def render_enum(enum: EmittedEnum) -> str:
    """Return the Python source for a single enum class."""
    lines = [f"class {enum.class_name}(str, Enum):"]
    for value in enum.values:
        member = screaming_snake(value)
        lines.append(f'    {member} = "{value}"')
    return "\n".join(lines)
