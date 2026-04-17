"""Snapshot test: regenerate against `mini_swagger.json` and diff vs. the
checked-in golden package under `tests/golden/kubex-k8s-1-30/`.

If the generator's output changes intentionally, regenerate the golden with:

    uv run python -m scripts.codegen generate \\
      --swagger scripts/codegen/tests/fixtures/mini_swagger.json \\
      --k8s-version 1.30 \\
      --output scripts/codegen/tests/golden \\
      --package-version 0.0.0.dev0

Reviewers see the diff in the PR so generator changes are auditable.
"""

from __future__ import annotations

import difflib
from pathlib import Path

import pytest

from scripts.codegen import model_emitter, resource_detector, spec_loader
from scripts.codegen.package_builder import RenderInputs, write_package

FIXTURE = Path(__file__).parent / "fixtures" / "mini_swagger.json"
GOLDEN_ROOT = Path(__file__).parent / "golden" / "kubex-k8s-1-30"


def _collect_relevant_files(root: Path) -> list[str]:
    """Walk the golden tree and return relative paths of all .py files."""
    base = root / "kubex" / "k8s" / "v1_30"
    if not base.exists():
        return []
    paths = []
    for p in sorted(base.rglob("*.py")):
        paths.append(str(p.relative_to(root)))
    return paths


_RELEVANT = _collect_relevant_files(GOLDEN_ROOT)


def _regenerate(tmp_path: Path) -> Path:
    spec = spec_loader.load_swagger(FIXTURE)
    resources = resource_detector.detect_resources(spec.definitions, spec.paths)
    build = model_emitter.build_modules(
        k8s_version_tag="v1_30",
        definitions=spec.definitions,
        resources=resources,
    )
    return write_package(
        RenderInputs(
            output_root=tmp_path,
            k8s_version="1.30",
            k8s_version_tag="v1_30",
            package_version="0.0.0.dev0",
            modules=build.modules,
            shared_enums=build.shared_enums,
        )
    )


@pytest.mark.parametrize("relative", _RELEVANT)
def test_generated_matches_golden(tmp_path: Path, relative: str) -> None:
    pkg = _regenerate(tmp_path)
    actual_path = pkg / relative
    expected_path = GOLDEN_ROOT / relative
    assert actual_path.is_file(), f"generator did not produce {relative}"
    assert expected_path.is_file(), (
        f"missing golden file {expected_path}; "
        "regenerate the golden with `python -m scripts.codegen generate "
        "--output scripts/codegen/tests/golden ...`"
    )
    actual = actual_path.read_text()
    expected = expected_path.read_text()
    if actual != expected:
        diff = "".join(
            difflib.unified_diff(
                expected.splitlines(keepends=True),
                actual.splitlines(keepends=True),
                fromfile=f"golden/{relative}",
                tofile=f"generated/{relative}",
            )
        )
        pytest.fail(
            f"Generated {relative} differs from the golden snapshot.\n"
            f"Regenerate with: uv run python -m scripts.codegen generate "
            f"--swagger scripts/codegen/tests/fixtures/mini_swagger.json "
            f"--k8s-version 1.30 --output scripts/codegen/tests/golden "
            f"--package-version 0.0.0.dev0\n\n{diff}"
        )
