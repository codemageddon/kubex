"""Load a Kubernetes OpenAPI v2 swagger.json (with optional v3 supplement).

The v3 per-group files (if present) are only consulted for definitions that the
v2 swagger.json omits. This lets newer alpha/beta types that ship v3-only
(e.g. some admissionregistration.k8s.io types) be generated, while keeping the
v2 spec as the primary source of truth for established resources.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class LoadedSpec:
    """A swagger document normalized for consumption by the generator."""

    definitions: dict[str, dict[str, Any]] = field(default_factory=dict)
    paths: dict[str, dict[str, Any]] = field(default_factory=dict)
    info: dict[str, Any] = field(default_factory=dict)


def load_swagger(path: str | Path) -> LoadedSpec:
    """Read a Kubernetes OpenAPI v2 swagger.json and normalize it."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return LoadedSpec(
        definitions=dict(data.get("definitions", {})),
        paths=dict(data.get("paths", {})),
        info=dict(data.get("info", {})),
    )


def merge_v3_supplement(spec: LoadedSpec, v3_dir: str | Path) -> LoadedSpec:
    """Fold v3 per-group files into `spec.definitions` for any missing definitions.

    Existing keys in `spec.definitions` win; v3 only fills in gaps. The v3 format
    uses `components.schemas` instead of `definitions`, with slightly different
    `$ref` paths — we translate refs so they align with the v2 namespace.
    """
    v3_root = Path(v3_dir)
    if not v3_root.is_dir():
        return spec
    for file in sorted(v3_root.glob("*.json")):
        data = json.loads(file.read_text(encoding="utf-8"))
        schemas = data.get("components", {}).get("schemas", {}) or {}
        for name, schema in schemas.items():
            spec.definitions.setdefault(name, _translate_v3_refs(schema))
    return spec


def _translate_v3_refs(obj: Any) -> Any:
    """Rewrite `#/components/schemas/X` refs to `#/definitions/X` in-place."""
    if isinstance(obj, dict):
        translated: dict[str, Any] = {}
        for k, v in obj.items():
            if (
                k == "$ref"
                and isinstance(v, str)
                and v.startswith("#/components/schemas/")
            ):
                translated[k] = "#/definitions/" + v.removeprefix(
                    "#/components/schemas/"
                )
            else:
                translated[k] = _translate_v3_refs(v)
        return translated
    if isinstance(obj, list):
        return [_translate_v3_refs(v) for v in obj]
    return obj
