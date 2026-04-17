"""Render `EmittedModule`s through Jinja and write the package to disk.

Produces a directory tree:

    packages/kubex-k8s-1-30/
    ├── pyproject.toml
    ├── README.md
    └── kubex/k8s/v1_30/
        ├── __init__.py
        ├── _common.py
        ├── core/
        │   └── v1/
        │       ├── __init__.py
        │       ├── pod.py
        │       └── ...
        └── ...

`kubex` and `kubex.k8s` are PEP 420 namespace — we do *not* create
`__init__.py` files for those intermediate packages.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from scripts.codegen import enum_emitter
from scripts.codegen.ir import EmittedClass, EmittedField, EmittedModule

_TEMPLATE_DIR = Path(__file__).parent / "templates"


@dataclass
class RenderInputs:
    """Inputs to `write_package`."""

    output_root: Path  # e.g. packages/
    k8s_version: str  # "1.30"
    k8s_version_tag: str  # "v1_30"
    package_version: str  # package release version string
    modules: dict[str, EmittedModule]
    shared_enums: list[enum_emitter.EmittedEnum]  # enums destined for _common.py


def write_package(inputs: RenderInputs) -> Path:
    """Render everything and write to disk. Returns the package root path."""
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    k8s_version_dashed = inputs.k8s_version.replace(".", "-")
    pkg_root = inputs.output_root / f"kubex-k8s-{k8s_version_dashed}"
    src_root = pkg_root / "kubex" / "k8s" / inputs.k8s_version_tag
    src_root.mkdir(parents=True, exist_ok=True)

    # pyproject.toml, README.
    pyproject = env.get_template("pyproject.toml.j2").render(
        k8s_version=inputs.k8s_version,
        k8s_version_dashed=k8s_version_dashed,
        package_version=inputs.package_version,
    )
    (pkg_root / "pyproject.toml").write_text(pyproject)
    readme_path = pkg_root / "README.md"
    if not readme_path.exists():
        readme_path.write_text(
            f"# kubex-k8s-{k8s_version_dashed}\n\nPydantic v2 models for Kubernetes {inputs.k8s_version}.\n"
        )

    # PEP 561 py.typed marker for the generated package.
    (src_root / "py.typed").write_text("")

    # _common.py
    common_src = env.get_template("common.py.j2").render(
        has_enums=bool(inputs.shared_enums),
        enums=[enum_emitter.render_enum(e) for e in inputs.shared_enums],
    )
    (src_root / "_common.py").write_text(common_src)

    # Per-class modules.
    base_prefix = f"kubex.k8s.{inputs.k8s_version_tag}"
    created_dirs: set[Path] = set()
    all_class_names: list[str] = []
    module_tpl = env.get_template("module.py.j2")

    for module in inputs.modules.values():
        rendered_classes = [_render_class(c) for c in module.classes]
        rendered_enums = [enum_emitter.render_enum(e) for e in module.enums]
        source = module_tpl.render(
            imports=module.imports.render(),
            classes=rendered_classes,
            enums=rendered_enums,
            trailing_assignments=module.trailing_assignments,
        )
        source = _collapse_blanks(source)

        # Derive nested path from module_path.
        relative = module.module_path.removeprefix(base_prefix + ".")
        parts = relative.split(".")
        dir_parts = parts[:-1]
        file_part = parts[-1] + ".py"

        if dir_parts:
            dir_path = src_root / Path(*dir_parts)
            if dir_path not in created_dirs:
                dir_path.mkdir(parents=True, exist_ok=True)
                # Create __init__.py for each intermediate package.
                for i in range(1, len(dir_parts) + 1):
                    init_dir = src_root / Path(*dir_parts[:i])
                    init_file = init_dir / "__init__.py"
                    if not init_file.exists():
                        init_file.write_text("")
                created_dirs.add(dir_path)
            (dir_path / file_part).write_text(source)
        else:
            (src_root / file_part).write_text(source)

        for c in module.classes:
            all_class_names.append(c.class_name)

    # __init__.py — just __all__, no re-exports, no INDEX.
    all_class_names.sort()
    init_src = env.get_template("package_init.py.j2").render(
        all_names=all_class_names,
    )
    (src_root / "__init__.py").write_text(init_src)

    # Always run ruff format + `check --fix` so output is idempotent.
    # These sort imports (requires rules I-001) and tidy whitespace; without
    # them the snapshot test downstream would hit cosmetic diffs.
    subprocess.run(
        [
            "uv",
            "run",
            "ruff",
            "check",
            "--select",
            "I",
            "--fix",
            "--quiet",
            str(src_root),
        ],
        check=False,
    )
    subprocess.run(
        ["uv", "run", "ruff", "format", "--quiet", str(src_root)],
        check=False,
    )
    return pkg_root


def _render_class(cls: EmittedClass) -> str:
    """Render one Pydantic class to source."""
    lines: list[str] = []
    bases = ", ".join(cls.bases) if cls.bases else "BaseK8sModel"
    lines.append(f"class {cls.class_name}({bases}):")
    if cls.docstring:
        lines.append(f'    """{cls.docstring}"""')
    if cls.resource_info is not None:
        info = cls.resource_info
        scope = "Scope.NAMESPACE" if info.is_namespaced else "Scope.CLUSTER"
        group_expr = '"core"' if info.group == "core" else f'"{info.group}"'
        lines.append(
            f'    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["{info.kind}"]] = ResourceConfig["{info.kind}"]('
        )
        lines.append(f'        version="{info.version}",')
        lines.append(f'        kind="{info.kind}",')
        lines.append(f"        group={group_expr},")
        lines.append(f'        plural="{info.plural}",')
        lines.append(f"        scope={scope},")
        lines.append("    )")
    for field_ in cls.fields:
        lines.append(_render_field(field_, cls.class_name))
    if len(lines) == 1:
        lines.append("    pass")
    return "\n".join(lines)


def _render_field(field_: EmittedField, class_name: str) -> str:
    alias_arg = f'alias="{field_.alias}"'
    if field_.default_expression is not None:
        default_part = field_.default_expression
        annotation = field_.type_expression
    elif field_.required:
        default_part = "..."
        annotation = field_.type_expression
    else:
        default_part = "default=None"
        annotation = f"{field_.type_expression} | None"
    desc_part = ""
    if field_.description:
        # Escape embedded double quotes.
        safe = field_.description.replace("\\", "\\\\").replace('"', '\\"')
        desc_part = f', description="{safe}"'
    return (
        f"    {field_.python_name}: {annotation} = "
        f"Field({default_part}, {alias_arg}{desc_part})"
    )


def _collapse_blanks(source: str) -> str:
    """Collapse runs of 3+ blank lines into 2."""
    out_lines: list[str] = []
    blank_run = 0
    for line in source.splitlines():
        if line.strip():
            if blank_run:
                out_lines.extend([""] * min(blank_run, 2))
                blank_run = 0
            out_lines.append(line)
        else:
            blank_run += 1
    if blank_run:
        out_lines.extend([""] * min(blank_run, 1))
    return "\n".join(out_lines) + "\n"
