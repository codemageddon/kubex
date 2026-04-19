from __future__ import annotations

import time

from ..adapters.protocol import CAP_LOGS, ClientAdapter
from . import Scenario, ScenarioContext, ScenarioResult

DEFAULT_N_LINES = 500


async def stream_logs_n_lines(
    adapter: ClientAdapter, ctx: ScenarioContext
) -> ScenarioResult:
    """Stream N log lines from the emitter pod.

    Emitter prints `line-<i>` forever; adapter records per-line inter-arrival
    times for latency percentiles.
    """
    n = ctx.stream_count or DEFAULT_N_LINES
    t0 = time.perf_counter_ns()
    sample = await adapter.stream_logs(ctx.namespace, ctx.log_pod_name, n)
    t1 = time.perf_counter_ns()
    return ScenarioResult(
        work_ns=t1 - t0,
        per_event_ns=list(getattr(sample, "inter_arrival_ns", [])),
        items=int(getattr(sample, "count", 0)),
    )


SCENARIOS: list[Scenario] = [
    Scenario(
        name="stream_logs_n_lines",
        fn=stream_logs_n_lines,
        required_capabilities=frozenset({CAP_LOGS}),
        warmup_iters=1,
        measure_iters=3,
        description="Stream N log lines from a busybox emitter pod.",
    ),
]
