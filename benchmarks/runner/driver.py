"""Benchmark driver: orchestrate harness subprocesses and collect artifacts.

Run with:

    uv run --group benchmark python -m benchmarks.runner.driver \\
        --kubeconfig /tmp/kc.yaml \\
        --namespace bench-abc \\
        --artifacts benchmarks/.artifacts

The driver assumes the caller already has a K3s cluster running and a
namespace seeded with pods matching the relevant scenarios. Typical usage
routes through pytest + the benchmarks/conftest.py fixtures, which prepare
the cluster and then shell out to the driver — see README.md.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from ..adapters import ADAPTER_LOADERS
from ..scenarios import all_scenarios
from .report import build_report

# Adapter × scenario matrix. Entries map adapter name → which scenarios it
# serves. Kept here (not on each adapter) so we can spot asymmetries at a
# glance. `kubex-metadata-*` only runs list/get-shaped scenarios. Non-asyncio
# adapters are excluded from scenarios that require asyncio-only libraries.
SCENARIOS_BY_ADAPTER: dict[str, list[str]] = {
    "kubex-httpx-asyncio": [
        "single_get",
        "single_create_delete",
        "list_small",
        "list_medium",
        "list_large",
        "list_namespaces",
        "watch_n_events",
        "stream_logs_n_lines",
    ],
    "kubex-httpx-trio": [
        "single_get",
        "single_create_delete",
        "list_small",
        "list_medium",
        "list_large",
        "list_namespaces",
        "watch_n_events",
        "stream_logs_n_lines",
    ],
    "kubex-aiohttp-asyncio": [
        "single_get",
        "single_create_delete",
        "list_small",
        "list_medium",
        "list_large",
        "list_namespaces",
        "watch_n_events",
        "stream_logs_n_lines",
    ],
    "kubex-metadata-aiohttp-asyncio": [
        "single_get_metadata",
        "list_metadata_only",
    ],
    "k8s-asyncio": [
        "single_get",
        "single_create_delete",
        "list_small",
        "list_medium",
        "list_large",
        "list_namespaces",
        "list_metadata_only",  # asymmetric full-list counterpart
        "watch_n_events",
        "stream_logs_n_lines",
    ],
}

SCENARIO_SEEDED_PODS: dict[str, int] = {
    "list_small": 10,
    "list_medium": 100,
    "list_large": 500,
    "list_metadata_only": 100,
}


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="benchmarks.runner.driver")
    p.add_argument("--kubeconfig", required=True)
    p.add_argument("--namespace", required=True)
    p.add_argument("--seeded-prefix", default="seed-")
    p.add_argument("--log-pod", default="log-emitter")
    p.add_argument("--artifacts", default="benchmarks/.artifacts")
    p.add_argument("--report", default="benchmarks/report.md")
    p.add_argument("--csv", default="benchmarks/report.csv")
    p.add_argument(
        "--adapters",
        nargs="*",
        choices=sorted(ADAPTER_LOADERS),
        default=None,
        help="Subset of adapters to run. Default: all.",
    )
    p.add_argument(
        "--scenarios",
        nargs="*",
        default=None,
        help="Subset of scenario names to run. Default: all.",
    )
    p.add_argument("--no-memory", action="store_true")
    p.add_argument("--cpu-profile", action="store_true")
    p.add_argument("--warmup-iters", type=int, default=-1)
    p.add_argument("--measure-iters", type=int, default=-1)
    p.add_argument("--k8s-version", default="1.35")
    return p.parse_args(argv)


def _pair_plan(
    adapters: list[str] | None, scenarios: list[str] | None
) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    registered_scenarios = all_scenarios()
    for adapter_name, scenario_names in SCENARIOS_BY_ADAPTER.items():
        if adapters and adapter_name not in adapters:
            continue
        for scenario_name in scenario_names:
            if scenario_name not in registered_scenarios:
                continue
            if scenarios and scenario_name not in scenarios:
                continue
            pairs.append((adapter_name, scenario_name))
    return pairs


def _adapter_runtime(adapter_name: str) -> str:
    if adapter_name.endswith("-trio"):
        return "trio"
    return "asyncio"


def _run_pair(
    args: argparse.Namespace, adapter: str, scenario: str, artifacts_dir: Path
) -> Path:
    out = artifacts_dir / f"{adapter}__{scenario}.json"
    cmd = [
        sys.executable,
        "-m",
        "benchmarks.runner.harness",
        "--adapter",
        adapter,
        "--scenario",
        scenario,
        "--kubeconfig",
        args.kubeconfig,
        "--namespace",
        args.namespace,
        "--seeded-prefix",
        args.seeded_prefix,
        "--log-pod",
        args.log_pod,
        "--runtime",
        _adapter_runtime(adapter),
        "--out",
        str(out),
        "--k8s-version",
        args.k8s_version,
        "--list-size",
        str(SCENARIO_SEEDED_PODS.get(scenario, 0)),
    ]
    if args.no_memory:
        cmd.append("--no-memory")
    if args.cpu_profile:
        cmd.append("--cpu-profile")
    if args.warmup_iters >= 0:
        cmd.extend(["--warmup-iters", str(args.warmup_iters)])
    if args.measure_iters >= 0:
        cmd.extend(["--measure-iters", str(args.measure_iters)])

    print(f"[driver] {adapter}  ->  {scenario}", flush=True)
    proc = subprocess.run(cmd, check=False)
    if proc.returncode != 0:
        print(
            f"[driver] FAILED {adapter} / {scenario} (rc={proc.returncode})",
            file=sys.stderr,
        )
    return out


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    artifacts_dir = Path(args.artifacts)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    pairs = _pair_plan(args.adapters, args.scenarios)
    if not pairs:
        print("[driver] no (adapter, scenario) pairs to run", file=sys.stderr)
        return 1

    for adapter, scenario in pairs:
        _run_pair(args, adapter, scenario, artifacts_dir)

    build_report(artifacts_dir, Path(args.report), Path(args.csv), args.k8s_version)
    print(f"[driver] report written to {args.report}")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    raise SystemExit(main())
