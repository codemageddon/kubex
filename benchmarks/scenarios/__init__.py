from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable


@dataclass(frozen=True)
class ScenarioContext:
    """Runtime inputs passed to every scenario body.

    Scenarios are pure functions of (adapter, context). The harness populates
    this based on CLI flags; keep additions here rather than adding positional
    args so scenarios stay interchangeable.
    """

    namespace: str
    seeded_pods_prefix: str
    log_pod_name: str
    list_size: int = 0
    stream_count: int = 0
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ScenarioResult:
    """Per-iteration payload returned by a scenario body.

    `work_ns` is the iteration's own perf_counter measurement (useful when the
    scenario does internal work the harness should not time, e.g. watch setup
    vs event reception). `per_event_ns` is populated only by streaming
    scenarios.
    """

    work_ns: int
    per_event_ns: list[int] = field(default_factory=list)
    items: int = 0


ScenarioFn = Callable[[Any, ScenarioContext], Awaitable[ScenarioResult]]


@dataclass(frozen=True)
class Scenario:
    name: str
    fn: ScenarioFn
    required_capabilities: frozenset[str]
    warmup_iters: int = 3
    measure_iters: int = 10
    description: str = ""
    # When True, asymmetric cross-library comparison — render with a caveat.
    asymmetric: bool = False


def _lazy_registry() -> dict[str, Scenario]:
    from . import list_ops, logs_ops, single_ops, watch_ops

    registry: dict[str, Scenario] = {}
    for mod in (single_ops, list_ops, watch_ops, logs_ops):
        for scenario in mod.SCENARIOS:
            registry[scenario.name] = scenario
    return registry


def all_scenarios() -> dict[str, Scenario]:
    return _lazy_registry()


def get_scenario(name: str) -> Scenario:
    try:
        return _lazy_registry()[name]
    except KeyError as exc:
        raise ValueError(
            f"Unknown scenario {name!r}. Known: {sorted(_lazy_registry())}"
        ) from exc


__all__ = [
    "Scenario",
    "ScenarioContext",
    "ScenarioFn",
    "ScenarioResult",
    "all_scenarios",
    "get_scenario",
]
