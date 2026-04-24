"""CLI entry point for the Kubex code generator.

Usage:

    python -m scripts.codegen generate \\
        --swagger ./openapi/1.30/swagger.json \\
        --v3-dir  ./openapi/1.30/v3 \\
        --k8s-version 1.30 \\
        --output  packages/
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Annotated

import typer

from scripts.codegen import model_emitter, resource_detector, spec_loader
from scripts.codegen.package_builder import RenderInputs, write_package

app = typer.Typer(
    add_completion=False,
    help="Generate and verify kubex-k8s-<version> resource packages.",
    no_args_is_help=True,
)


def _version_tag(k8s_version: str) -> str:
    """`1.30` -> `v1_30`."""
    return "v" + k8s_version.replace(".", "_")


def run_generate(
    swagger: Path,
    k8s_version: str,
    *,
    v3_dir: Path | None = None,
    package_version: str = "0.1.0-alpha.1",
    output: Path = Path("packages/"),
    only_groups: str | None = None,
    format: bool = True,
) -> Path:
    """Generate a kubex-k8s-* package from a swagger.json.

    Returns the path to the generated package root directory.
    """
    spec = spec_loader.load_swagger(swagger)
    if v3_dir is not None:
        spec_loader.merge_v3_supplement(spec, v3_dir)

    resources = resource_detector.detect_resources(spec.definitions, spec.paths)
    if only_groups:
        wanted = {g.strip() for g in only_groups.split(",") if g.strip()}
        resources = [r for r in resources if r.group in wanted]
        if not resources:
            msg = f"No resources matched --only-groups={only_groups}"
            raise ValueError(msg)

    k8s_version_tag = _version_tag(k8s_version)
    build = model_emitter.build_modules(
        k8s_version_tag=k8s_version_tag,
        definitions=spec.definitions,
        resources=resources,
    )
    pkg_root = write_package(
        RenderInputs(
            output_root=output,
            k8s_version=k8s_version,
            k8s_version_tag=k8s_version_tag,
            package_version=package_version,
            modules=build.modules,
            shared_enums=build.shared_enums,
        )
    )
    typer.echo(f"Wrote generated package to {pkg_root}")

    if format:
        subprocess.run(["uv", "run", "ruff", "format", str(pkg_root)], check=False)

    return pkg_root


@app.command()
def generate(
    swagger: Annotated[Path, typer.Option(help="Path to swagger.json")],
    k8s_version: Annotated[str, typer.Option(help='Kubernetes version, e.g. "1.30"')],
    v3_dir: Annotated[
        Path | None,
        typer.Option(help="Optional directory of v3 per-group files"),
    ] = None,
    package_version: Annotated[
        str, typer.Option(help="Generated package version")
    ] = "0.1.0-alpha.1",
    output: Annotated[Path, typer.Option(help="Output root directory")] = Path(
        "packages/"
    ),
    only_groups: Annotated[
        str | None,
        typer.Option(help='Comma-separated groups to emit (e.g. "core,apps")'),
    ] = None,
    format: Annotated[
        bool,
        typer.Option(
            "--format/--no-format",
            help="Run ruff format on the output (default: on).",
        ),
    ] = True,
) -> None:
    """Generate a kubex-k8s-* package from a swagger.json."""
    try:
        run_generate(
            swagger,
            k8s_version,
            v3_dir=v3_dir,
            package_version=package_version,
            output=output,
            only_groups=only_groups,
            format=format,
        )
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc


def run_verify(package: Path) -> int:
    """Run ruff/mypy against a generated package.

    Returns 0 on success, non-zero on failure.
    """
    rc = 0
    for cmd in (
        ["uv", "run", "ruff", "check", str(package)],
        ["uv", "run", "ruff", "format", "--check", str(package)],
    ):
        typer.echo(f"$ {' '.join(cmd)}")
        result = subprocess.run(cmd, check=False)
        if result.returncode != 0:
            rc = result.returncode
    # mypy must run from within the package directory so it resolves the
    # `kubex` namespace package correctly (the repo-root `kubex/` with its
    # own `__init__.py` would otherwise shadow the generated namespace).
    mypy_cmd = [
        "uv",
        "run",
        "mypy",
        "--strict",
        "--namespace-packages",
        "--explicit-package-bases",
        "kubex/",
    ]
    typer.echo(f"$ (cd {package}) {' '.join(mypy_cmd)}")
    result = subprocess.run(mypy_cmd, check=False, cwd=str(package))
    if result.returncode != 0:
        rc = result.returncode
    return rc


@app.command()
def verify(
    package: Annotated[Path, typer.Argument(help="Path to kubex-k8s-* package dir")],
) -> None:
    """Run ruff/mypy against a generated package."""
    raise typer.Exit(code=run_verify(package))


@app.command()
def regenerate(
    versions: Annotated[
        str,
        typer.Option(help='Comma-separated K8s minor versions, e.g. "1.32,1.33,1.35"'),
    ],
    cache_dir: Annotated[Path, typer.Option(help="Directory for cached specs")] = Path(
        ".cache/schemas"
    ),
    package_version: Annotated[
        str, typer.Option(help="Generated package version")
    ] = "0.1.0-alpha.1",
    output: Annotated[Path, typer.Option(help="Output root directory")] = Path(
        "packages/"
    ),
    do_verify: Annotated[
        bool,
        typer.Option(
            "--verify/--no-verify",
            help="Run ruff/mypy verification after generation (default: on).",
        ),
    ] = True,
) -> None:
    """Download latest K8s OpenAPI specs and regenerate all model packages."""
    from scripts.codegen.fetch_specs import download_specs, resolve_latest_release

    minor_versions = [v.strip() for v in versions.split(",") if v.strip()]
    if not minor_versions:
        typer.echo("No versions specified.", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Regenerating models for versions: {', '.join(minor_versions)}")

    results: dict[str, str] = {}
    for version in minor_versions:
        typer.echo(f"\n--- Processing K8s {version} ---")
        try:
            typer.echo(f"Resolving latest release for {version}...")
            tag = resolve_latest_release(version)
            typer.echo(f"Resolved {version} -> {tag}")
            specs = download_specs(tag, cache_dir)
        except Exception as exc:
            typer.echo(f"Fetch failed for {version}: {exc}", err=True)
            results[version] = f"fetch failed: {exc}"
            continue

        try:
            pkg_root = run_generate(
                specs.swagger_path,
                version,
                v3_dir=specs.v3_dir,
                package_version=package_version,
                output=output,
            )
        except Exception as exc:
            typer.echo(f"Generation failed for {version}: {exc}", err=True)
            results[version] = f"generate failed: {exc}"
            continue

        if do_verify:
            typer.echo(f"Verifying package for K8s {version}...")
            rc = run_verify(pkg_root)
            if rc != 0:
                results[version] = f"verify failed (exit code {rc})"
                continue

        results[version] = "ok"

    typer.echo("\n--- Summary ---")
    failed = False
    for version in minor_versions:
        status = results.get(version, "skipped")
        typer.echo(f"  {version}: {status}")
        if status != "ok":
            failed = True

    if failed:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
