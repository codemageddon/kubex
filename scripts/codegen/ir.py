"""Intermediate representation types for a generated package.

`EmittedField`, `EmittedClass`, and `EmittedModule` capture everything the
template layer needs to render a module. They don't carry any code — all
logic lives in `model_emitter` and `package_builder`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from scripts.codegen.enum_emitter import EmittedEnum
from scripts.codegen.imports import ImportSet
from scripts.codegen.resource_detector import ResourceInfo


@dataclass
class EmittedField:
    """One property on a generated class."""

    python_name: str
    alias: str
    type_expression: str
    required: bool
    description: str | None
    # Overrides `default=None` / `...` when set (e.g. Literal defaults on api_version).
    default_expression: str | None = None


@dataclass
class EmittedClass:
    """A Pydantic class to render in a module."""

    class_name: str
    bases: list[str]
    docstring: str | None
    fields: list[EmittedField]
    # A resource class gets a `__RESOURCE_CONFIG__` literal.
    resource_info: ResourceInfo | None = None
    # A list class is wired via a trailing assignment; carries the single
    # owner so the emitter can write `Owner.__RESOURCE_CONFIG__._list_model = ClsName`.
    list_owner_class: str | None = None


@dataclass
class EmittedModule:
    """All state needed to render one `core_v1.py`-shaped file."""

    module_path: str  # dotted: "kubex.k8s.v1_30.core_v1"
    file_name: str  # "core_v1.py"
    classes: list[EmittedClass] = field(default_factory=list)
    enums: list[EmittedEnum] = field(default_factory=list)
    imports: ImportSet = field(default_factory=ImportSet)
    trailing_assignments: list[str] = field(default_factory=list)


@dataclass
class BuildResult:
    """Output of `build_modules`: the per-group modules plus any shared enums."""

    modules: dict[str, EmittedModule]
    shared_enums: list[EmittedEnum]
