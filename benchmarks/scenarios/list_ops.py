from __future__ import annotations

import time

from ..adapters.protocol import (
    CAP_METADATA,
    CAP_NAMESPACE_LIST,
    CAP_POD_CRUD,
    ClientAdapter,
)
from . import Scenario, ScenarioContext, ScenarioResult


async def _list_pods(adapter: ClientAdapter, ctx: ScenarioContext) -> ScenarioResult:
    limit = ctx.list_size if ctx.list_size > 0 else None
    t0 = time.perf_counter_ns()
    count = await adapter.list_pods(ctx.namespace, limit=limit)
    t1 = time.perf_counter_ns()
    return ScenarioResult(work_ns=t1 - t0, items=count)


async def list_small(adapter: ClientAdapter, ctx: ScenarioContext) -> ScenarioResult:
    """List a namespace seeded with ~10 pods."""
    return await _list_pods(adapter, ctx)


async def list_medium(adapter: ClientAdapter, ctx: ScenarioContext) -> ScenarioResult:
    """List a namespace seeded with ~100 pods."""
    return await _list_pods(adapter, ctx)


async def list_large(adapter: ClientAdapter, ctx: ScenarioContext) -> ScenarioResult:
    """List a namespace seeded with ~500 pods. Headline memory scenario."""
    return await _list_pods(adapter, ctx)


async def list_metadata_only(
    adapter: ClientAdapter, ctx: ScenarioContext
) -> ScenarioResult:
    """Kubex PartialObjectMetadata list vs. kubernetes-asyncio full list.

    kubernetes-asyncio has no metadata-only equivalent, so its row of this
    scenario is a full list of the same namespace; the report flags the
    comparison as asymmetric.
    """
    return await _list_pods(adapter, ctx)


async def list_namespaces(
    adapter: ClientAdapter, ctx: ScenarioContext
) -> ScenarioResult:
    t0 = time.perf_counter_ns()
    count = await adapter.list_namespaces()
    t1 = time.perf_counter_ns()
    return ScenarioResult(work_ns=t1 - t0, items=count)


# The same required_capabilities set works for full-list and metadata-list:
# adapters that claim CAP_METADATA serve list_pods through list_metadata.
_LIST_CAPS = frozenset({CAP_POD_CRUD}) | frozenset({CAP_METADATA})


SCENARIOS: list[Scenario] = [
    Scenario(
        name="list_small",
        fn=list_small,
        required_capabilities=frozenset(),
        description="List ~10 pods in bench namespace.",
    ),
    Scenario(
        name="list_medium",
        fn=list_medium,
        required_capabilities=frozenset(),
        description="List ~100 pods in bench namespace.",
    ),
    Scenario(
        name="list_large",
        fn=list_large,
        required_capabilities=frozenset(),
        description="List ~500 pods in bench namespace.",
    ),
    Scenario(
        name="list_metadata_only",
        fn=list_metadata_only,
        required_capabilities=frozenset(),
        description=(
            "Kubex PartialObjectMetadata list vs. kubernetes-asyncio full list "
            "(asymmetric — kubernetes-asyncio has no metadata-only equivalent)."
        ),
        asymmetric=True,
    ),
    Scenario(
        name="list_namespaces",
        fn=list_namespaces,
        required_capabilities=frozenset({CAP_NAMESPACE_LIST}),
        description="List all namespaces (cluster-scoped).",
    ),
]


# Scenarios have empty required_capabilities because both full-list and
# metadata-list adapters serve `list_pods` — the capability gate is enforced
# by which adapters the driver picks for each scenario, not by the scenario
# itself. _LIST_CAPS is retained for documentation.
__all__ = ["SCENARIOS", "_LIST_CAPS"]
