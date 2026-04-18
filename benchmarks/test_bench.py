"""In-process wall-time + latency benchmarks via pytest-benchmark.

This module is complementary to the subprocess-based driver — use it for:

  - Quick wall-time regressions during development.
  - Runs on machines without memray (e.g. Windows).

For memory/allocation numbers, run the driver instead:

    uv run --group benchmark python -m benchmarks.run

Tests are synchronous: they own a private event loop, perform adapter
setup/teardown around the benchmark block, and use ``benchmark(...)`` on a
sync wrapper that drives the async scenario via ``loop.run_until_complete``.
This avoids fighting pytest-anyio's event-loop ownership and keeps
pytest-benchmark's timing semantics intact.

Streaming scenarios (watch_n_events, stream_logs_n_lines) are excluded
because their timing is dominated by server-side event generation, not
client code.
"""

from __future__ import annotations

import asyncio
from typing import Any, Iterator

import pytest

from .adapters import load_adapter
from .scenarios import ScenarioContext, get_scenario

NON_STREAMING_SCENARIOS = [
    "single_get",
    "single_create_delete",
    "list_small",
    "list_medium",
    "list_large",
    "list_namespaces",
]

ADAPTERS_WITH_RUNTIME = [
    "kubex-httpx-asyncio",
    "kubex-aiohttp-asyncio",
    "k8s-asyncio",
]


@pytest.fixture
def event_loop() -> Iterator[asyncio.AbstractEventLoop]:
    loop = asyncio.new_event_loop()
    try:
        yield loop
    finally:
        loop.close()


@pytest.fixture
def adapter(
    request: pytest.FixtureRequest,
    event_loop: asyncio.AbstractEventLoop,
    k3s_kubeconfig: str,
    seeded_namespace: str,
) -> Iterator[object]:
    adapter_name = request.param
    cls = load_adapter(adapter_name)
    inst = cls()
    event_loop.run_until_complete(inst.setup(k3s_kubeconfig))
    try:
        yield inst
    finally:
        event_loop.run_until_complete(inst.teardown())


@pytest.mark.parametrize("adapter", ADAPTERS_WITH_RUNTIME, indirect=True)
@pytest.mark.parametrize("scenario_name", NON_STREAMING_SCENARIOS)
def test_scenario_wall_time(
    benchmark: Any,
    adapter: object,
    event_loop: asyncio.AbstractEventLoop,
    seeded_namespace: str,
    scenario_name: str,
) -> None:
    scenario = get_scenario(scenario_name)
    ctx = ScenarioContext(
        namespace=seeded_namespace,
        seeded_pods_prefix="seed-",
        log_pod_name="log-emitter",
    )

    def run() -> None:
        event_loop.run_until_complete(scenario.fn(adapter, ctx))

    benchmark(run)
