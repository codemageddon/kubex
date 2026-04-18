from __future__ import annotations

import time
import uuid

from ..adapters.protocol import CAP_METADATA, CAP_POD_CRUD, ClientAdapter, PodSpecLite
from . import Scenario, ScenarioContext, ScenarioResult


async def single_get(adapter: ClientAdapter, ctx: ScenarioContext) -> ScenarioResult:
    """Read one pre-seeded pod by name. Measures hot-path GET."""
    target = f"{ctx.seeded_pods_prefix}0"
    t0 = time.perf_counter_ns()
    await adapter.get_pod(ctx.namespace, target)
    t1 = time.perf_counter_ns()
    return ScenarioResult(work_ns=t1 - t0, items=1)


async def single_create_delete(
    adapter: ClientAdapter, ctx: ScenarioContext
) -> ScenarioResult:
    """Full create then delete of one pod. Measures serialization round-trip."""
    name = f"bench-{uuid.uuid4().hex[:10]}"
    spec = PodSpecLite(name=name)
    t0 = time.perf_counter_ns()
    await adapter.create_pod(ctx.namespace, spec)
    await adapter.delete_pod(ctx.namespace, name)
    t1 = time.perf_counter_ns()
    return ScenarioResult(work_ns=t1 - t0, items=1)


SCENARIOS: list[Scenario] = [
    Scenario(
        name="single_get",
        fn=single_get,
        required_capabilities=frozenset({CAP_POD_CRUD}) | frozenset(),
        description="Single pod GET against a pre-seeded namespace.",
    ),
    Scenario(
        name="single_get_metadata",
        fn=single_get,
        required_capabilities=frozenset({CAP_METADATA}),
        description="Single pod GET via PartialObjectMetadata (kubex-only).",
        asymmetric=True,
    ),
    Scenario(
        name="single_create_delete",
        fn=single_create_delete,
        required_capabilities=frozenset({CAP_POD_CRUD}),
        description="Create then delete one lightweight pause pod.",
    ),
]
