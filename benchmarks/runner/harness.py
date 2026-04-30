"""Subprocess-invocable benchmark harness.

Runs exactly ONE (adapter, scenario) pair in the current process and emits a
Metrics JSON artifact. The driver spawns one process per (adapter, scenario)
combo so:

  - Library imports never cross-contaminate (kubex and kubernetes-asyncio
    never coexist in the same interpreter, so their module pages/caches
    cannot inflate or dampen each other's RSS numbers).
  - GC state starts fresh.
  - memray hooks run against a clean allocator.

Not intended to be called directly by users in most cases — prefer
``python -m benchmarks.runner.driver``. Direct invocation is supported for
ad-hoc runs and debugging.
"""

from __future__ import annotations

import argparse
import gc
import statistics
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path
from typing import Any

from ..adapters import load_adapter
from ..scenarios import ScenarioContext, get_scenario
from .metrics import LatencyStats, Metrics, dumps


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="benchmarks.runner.harness",
        description="Run one (adapter, scenario) benchmark and emit a JSON artifact.",
    )
    p.add_argument("--adapter", required=True)
    p.add_argument("--scenario", required=True)
    p.add_argument("--kubeconfig", required=True)
    p.add_argument("--namespace", required=True)
    p.add_argument("--seeded-prefix", default="seed-")
    p.add_argument("--log-pod", default="log-emitter")
    p.add_argument("--list-size", type=int, default=0)
    p.add_argument("--stream-count", type=int, default=0)
    p.add_argument(
        "--runtime",
        choices=("asyncio", "trio"),
        default="asyncio",
    )
    p.add_argument("--out", required=True, help="Path for metrics JSON.")
    p.add_argument(
        "--k8s-version",
        default="1.33",
        help="Server K8s version label (for reporting; does not control wire).",
    )
    p.add_argument(
        "--no-memory",
        action="store_true",
        help="Disable memray + tracemalloc; report zero memory metrics.",
    )
    p.add_argument(
        "--cpu-profile",
        action="store_true",
        help="Enable pyinstrument. Perturbs wall-time; run separately for CPU.",
    )
    p.add_argument(
        "--warmup-iters",
        type=int,
        default=-1,
        help="Override scenario's default warmup iterations.",
    )
    p.add_argument(
        "--measure-iters",
        type=int,
        default=-1,
        help="Override scenario's default measure iterations.",
    )
    return p.parse_args(argv)


async def _run_once(
    adapter: Any, scenario: Any, ctx: ScenarioContext
) -> tuple[int, list[int], int]:
    result = await scenario.fn(adapter, ctx)
    return result.work_ns, result.per_event_ns, result.items


async def _main_async(args: argparse.Namespace) -> Metrics:
    adapter_cls = load_adapter(args.adapter)
    scenario = get_scenario(args.scenario)
    adapter = adapter_cls()

    ctx = ScenarioContext(
        namespace=args.namespace,
        seeded_pods_prefix=args.seeded_prefix,
        log_pod_name=args.log_pod,
        list_size=args.list_size,
        stream_count=args.stream_count,
    )

    await adapter.setup(args.kubeconfig)

    warmup = args.warmup_iters if args.warmup_iters >= 0 else scenario.warmup_iters
    measure = args.measure_iters if args.measure_iters >= 0 else scenario.measure_iters

    wall_ns: list[int] = []
    per_event_ns: list[int] = []
    items: list[int] = []

    try:
        for _ in range(warmup):
            await _run_once(adapter, scenario, ctx)

        gc.collect()

        profiler = None
        if args.cpu_profile:
            import pyinstrument

            profiler = pyinstrument.Profiler(async_mode="enabled")
            profiler.start()

        cpu_t0 = time.process_time()
        for _ in range(measure):
            w, events, n = await _run_once(adapter, scenario, ctx)
            wall_ns.append(w)
            per_event_ns.extend(events)
            items.append(n)
        cpu_t1 = time.process_time()

        cpu_seconds = cpu_t1 - cpu_t0
        if profiler is not None:
            profiler.stop()
            try:
                speedscope_dir = Path(args.out).parent
                speedscope_path = speedscope_dir / (
                    f"{args.adapter}__{args.scenario}.speedscope.json"
                )
                speedscope_path.write_text(
                    profiler.output(renderer=_speedscope_renderer())
                )
            except Exception:
                pass
    finally:
        await adapter.teardown()

    return Metrics(
        adapter=args.adapter,
        scenario=args.scenario,
        runtime=args.runtime,
        k8s_version=args.k8s_version,
        iterations=len(wall_ns),
        items_mean=statistics.fmean(items) if items else 0.0,
        wall=LatencyStats.from_samples(wall_ns),
        per_event=LatencyStats.from_samples(per_event_ns),
        peak_rss_bytes=0,
        total_bytes_alloc=0,
        total_allocations=0,
        steady_heap_bytes=0,
        cpu_seconds=cpu_seconds,
        asymmetric=scenario.asymmetric,
        notes=[scenario.description] if scenario.description else [],
    )


def _speedscope_renderer() -> Any:
    from pyinstrument.renderers.speedscope import (
        SpeedscopeRenderer,
    )

    return SpeedscopeRenderer()


def _run_anyio(coro_fn: Any, backend: str) -> Metrics:
    import anyio

    result: Metrics = anyio.run(coro_fn, backend=backend)
    return result


def _run_with_memory(args: argparse.Namespace) -> Metrics:
    """Wraps the async run with memray + tracemalloc.

    memray hooks the allocator at import-time setup, so it must wrap the full
    async run. We then re-read the memray output to extract stats.
    """
    tracemalloc.start(25)
    memray_path = Path(tempfile.mkstemp(prefix="memray-", suffix=".bin")[1])
    memray_path.unlink(missing_ok=True)  # memray refuses to overwrite

    import memray

    with memray.Tracker(str(memray_path), native_traces=False):
        metrics = _run_anyio(lambda: _main_async(args), args.runtime)

    gc.collect()
    heap_current, _ = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    peak = 0
    total_bytes = 0
    total_allocs = 0
    try:
        reader = memray.FileReader(str(memray_path))
        meta = reader.metadata
        peak = int(getattr(meta, "peak_memory", 0) or 0)
        total_bytes = int(
            getattr(meta, "total_bytes_allocated", 0)
            or getattr(meta, "total_memory_allocated", 0)
            or 0
        )
        total_allocs = int(getattr(meta, "total_allocations", 0) or 0)
    except Exception as exc:  # pragma: no cover
        metrics = _replace(
            metrics, notes=[*metrics.notes, f"memray read failed: {exc}"]
        )
    finally:
        memray_path.unlink(missing_ok=True)

    return _replace(
        metrics,
        peak_rss_bytes=peak,
        total_bytes_alloc=total_bytes,
        total_allocations=total_allocs,
        steady_heap_bytes=heap_current,
    )


def _replace(metrics: Metrics, **kwargs: Any) -> Metrics:
    from dataclasses import replace

    return replace(metrics, **kwargs)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    if args.no_memory:
        metrics = _run_anyio(lambda: _main_async(args), args.runtime)
    else:
        metrics = _run_with_memory(args)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(dumps(metrics))
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    raise SystemExit(main())
