"""CLI entry point for the Kubex code generator.

Usage:

    python -m scripts.codegen generate \\
        --swagger ./openapi/1.30/swagger.json \\
        --v3-dir  ./openapi/1.30/v3 \\
        --k8s-version 1.30 \\
        --output  packages/
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from scripts.codegen import model_emitter, resource_detector, spec_loader
from scripts.codegen.package_builder import RenderInputs, write_package


def _version_tag(k8s_version: str) -> str:
    """`1.30` -> `v1_30`."""
    return "v" + k8s_version.replace(".", "_")


def cmd_generate(args: argparse.Namespace) -> int:
    spec = spec_loader.load_swagger(args.swagger)
    if args.v3_dir:
        spec_loader.merge_v3_supplement(spec, args.v3_dir)

    resources = resource_detector.detect_resources(spec.definitions, spec.paths)
    if args.only_groups:
        wanted = {g.strip() for g in args.only_groups.split(",") if g.strip()}
        resources = [r for r in resources if r.group in wanted]
        if not resources:
            print(
                f"No resources matched --only-groups={args.only_groups}",
                file=sys.stderr,
            )
            return 1

    k8s_version_tag = _version_tag(args.k8s_version)
    build = model_emitter.build_modules(
        k8s_version_tag=k8s_version_tag,
        definitions=spec.definitions,
        resources=resources,
    )

    inputs = RenderInputs(
        output_root=Path(args.output),
        k8s_version=args.k8s_version,
        k8s_version_tag=k8s_version_tag,
        package_version=args.package_version,
        modules=build.modules,
        shared_enums=build.shared_enums,
    )
    pkg_root = write_package(inputs)
    print(f"Wrote generated package to {pkg_root}")

    if args.format:
        _run_ruff_format(pkg_root)
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    """Validate a generated package: ruff, format, mypy, smoke-import."""
    pkg = Path(args.package)
    rc = 0
    for cmd in (
        ["uv", "run", "ruff", "check", str(pkg)],
        ["uv", "run", "ruff", "format", "--check", str(pkg)],
        ["uv", "run", "mypy", "--strict", str(pkg / "src")],
    ):
        print(f"$ {' '.join(cmd)}")
        result = subprocess.run(cmd, check=False)
        if result.returncode != 0:
            rc = result.returncode
    return rc


def _run_ruff_format(pkg_root: Path) -> None:
    subprocess.run(["uv", "run", "ruff", "format", str(pkg_root)], check=False)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="scripts.codegen")
    sub = parser.add_subparsers(dest="cmd", required=True)

    gen = sub.add_parser(
        "generate", help="Generate a kubex-k8s-* package from a swagger.json"
    )
    gen.add_argument("--swagger", required=True, help="Path to swagger.json")
    gen.add_argument(
        "--v3-dir", default=None, help="Optional directory of v3 per-group files"
    )
    gen.add_argument(
        "--k8s-version", required=True, help='Kubernetes version, e.g. "1.30"'
    )
    gen.add_argument(
        "--package-version", default="0.1.0-alpha.1", help="Generated package version"
    )
    gen.add_argument("--output", default="packages/", help="Output root directory")
    gen.add_argument(
        "--only-groups",
        default=None,
        help='Comma-separated list of groups to emit (e.g. "core,apps")',
    )
    gen.add_argument(
        "--format",
        dest="format",
        action="store_true",
        default=True,
        help="Run ruff format on the output",
    )
    gen.add_argument(
        "--no-format",
        dest="format",
        action="store_false",
        help="Skip ruff format on the output",
    )
    gen.set_defaults(func=cmd_generate)

    verify = sub.add_parser("verify", help="Run ruff/mypy against a generated package")
    verify.add_argument("package", help="Path to kubex-k8s-* package directory")
    verify.set_defaults(func=cmd_verify)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
