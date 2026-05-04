"""End-to-end orchestrator: start K3s, seed, run driver, tear down.

Intended entry point for full benchmark runs (memory + CPU + latency):

    uv run --group benchmark python -m benchmarks.run \\
        --report benchmarks/report.md

Separate from `benchmarks.runner.driver`, which expects an existing cluster
and kubeconfig — the driver is useful when you already have a long-lived
cluster and want to re-measure without paying K3s boot cost repeatedly.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from ._cluster import (
    k3s_cluster,
    k8s_version_from_image,
    seed_namespace,
    teardown_namespace,
)
from .runner.driver import main as driver_main


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="benchmarks.run")
    p.add_argument("--seed-pods", type=int, default=500)
    p.add_argument("--artifacts", default="benchmarks/.artifacts")
    p.add_argument("--report", default="benchmarks/report.md")
    p.add_argument("--csv", default="benchmarks/report.csv")
    p.add_argument("--adapters", nargs="*", default=None)
    p.add_argument("--scenarios", nargs="*", default=None)
    p.add_argument("--no-memory", action="store_true")
    p.add_argument("--cpu-profile", action="store_true")
    p.add_argument("--warmup-iters", type=int, default=-1)
    p.add_argument("--measure-iters", type=int, default=-1)
    return p.parse_args(argv)


async def _setup_and_run(args: argparse.Namespace) -> int:
    async with k3s_cluster() as kubeconfig_path:
        ns = await seed_namespace(kubeconfig_path, args.seed_pods)
        k8s_version = k8s_version_from_image()
        try:
            driver_argv = [
                "--kubeconfig",
                kubeconfig_path,
                "--namespace",
                ns,
                "--artifacts",
                args.artifacts,
                "--report",
                args.report,
                "--csv",
                args.csv,
                "--k8s-version",
                k8s_version,
            ]
            if args.adapters:
                driver_argv += ["--adapters", *args.adapters]
            if args.scenarios:
                driver_argv += ["--scenarios", *args.scenarios]
            if args.no_memory:
                driver_argv.append("--no-memory")
            if args.cpu_profile:
                driver_argv.append("--cpu-profile")
            if args.warmup_iters >= 0:
                driver_argv += ["--warmup-iters", str(args.warmup_iters)]
            if args.measure_iters >= 0:
                driver_argv += ["--measure-iters", str(args.measure_iters)]
            return driver_main(driver_argv)
        finally:
            await teardown_namespace(kubeconfig_path, ns)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    return asyncio.run(_setup_and_run(args))


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    raise SystemExit(main())
