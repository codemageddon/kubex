from __future__ import annotations

import time

try:
    import anyio
except ImportError:  # pragma: no cover - benchmarks group guarantees it
    anyio = None  # type: ignore[assignment]

from ..adapters.protocol import CAP_POD_CRUD, CAP_WATCH, ClientAdapter, PodSpecLite
from . import Scenario, ScenarioContext, ScenarioResult

DEFAULT_N_EVENTS = 50


async def _burst_create_delete(
    adapter: ClientAdapter, ctx: ScenarioContext, n: int
) -> None:
    """Sibling task that causes n/2 create+delete pairs → ~n watch events.

    We create and delete separately with a tiny pause so the watch receiver
    is pushed by distinct events rather than coalesced updates.
    """
    assert anyio is not None
    for i in range(max(1, n // 2)):
        name = f"watch-bench-{i}"
        try:
            await adapter.create_pod(ctx.namespace, PodSpecLite(name=name))
        except Exception:
            pass
        await anyio.sleep(0)
        try:
            await adapter.delete_pod(ctx.namespace, name)
        except Exception:
            pass
        await anyio.sleep(0)


async def watch_n_events(
    adapter: ClientAdapter, ctx: ScenarioContext
) -> ScenarioResult:
    """Receive N watch events while a sibling task bursts create/delete.

    Per-event inter-arrival times are returned as `per_event_ns` for latency
    percentiles; `work_ns` is the wall time from starting the receiver until
    N events have landed (includes sibling-burst time, which is roughly
    equal across adapters but noted in the README).
    """
    assert anyio is not None
    n = ctx.stream_count or DEFAULT_N_EVENTS

    async def receive(result: dict[str, object]) -> None:
        sample = await adapter.watch_pods(ctx.namespace, n)
        result["sample"] = sample

    t0 = time.perf_counter_ns()
    received: dict[str, object] = {}
    async with anyio.create_task_group() as tg:
        tg.start_soon(receive, received)
        await anyio.sleep(0.05)  # let watch connect before bursting
        tg.start_soon(_burst_create_delete, adapter, ctx, n)
    t1 = time.perf_counter_ns()

    sample = received["sample"]
    return ScenarioResult(
        work_ns=t1 - t0,
        per_event_ns=list(getattr(sample, "inter_arrival_ns", [])),
        items=int(getattr(sample, "count", 0)),
    )


SCENARIOS: list[Scenario] = [
    Scenario(
        name="watch_n_events",
        fn=watch_n_events,
        required_capabilities=frozenset({CAP_WATCH, CAP_POD_CRUD}),
        warmup_iters=1,
        measure_iters=3,
        description="Receive N watch events driven by a sibling create/delete burst.",
    ),
]
