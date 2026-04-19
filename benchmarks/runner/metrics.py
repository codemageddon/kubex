from __future__ import annotations

import json
import statistics
from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class LatencyStats:
    """Distribution summary for a list of latency samples in nanoseconds."""

    count: int
    mean_ns: float
    stddev_ns: float
    p50_ns: int
    p90_ns: int
    p95_ns: int
    p99_ns: int
    max_ns: int

    @classmethod
    def from_samples(cls, samples: list[int]) -> "LatencyStats":
        if not samples:
            return cls(0, 0.0, 0.0, 0, 0, 0, 0, 0)
        ordered = sorted(samples)
        mean = statistics.fmean(ordered)
        stddev = statistics.pstdev(ordered) if len(ordered) > 1 else 0.0
        return cls(
            count=len(ordered),
            mean_ns=mean,
            stddev_ns=stddev,
            p50_ns=_pct(ordered, 0.50),
            p90_ns=_pct(ordered, 0.90),
            p95_ns=_pct(ordered, 0.95),
            p99_ns=_pct(ordered, 0.99),
            max_ns=ordered[-1],
        )


def _pct(ordered: list[int], q: float) -> int:
    if not ordered:
        return 0
    idx = min(len(ordered) - 1, max(0, round(q * (len(ordered) - 1))))
    return ordered[idx]


@dataclass(frozen=True)
class Metrics:
    """Full metric payload emitted per (adapter, scenario) run."""

    adapter: str
    scenario: str
    runtime: str
    k8s_version: str
    iterations: int
    items_mean: float
    # Wall-time per iteration (from scenario-reported work_ns).
    wall: LatencyStats
    # Per-event latency for streaming scenarios (empty otherwise).
    per_event: LatencyStats
    # Memory — zero if memray disabled.
    peak_rss_bytes: int
    total_bytes_alloc: int
    total_allocations: int
    steady_heap_bytes: int
    # CPU — zero if pyinstrument disabled.
    cpu_seconds: float
    # Asymmetric scenarios flag a caveat in the report.
    asymmetric: bool = False
    notes: list[str] = field(default_factory=list)


def dumps(metrics: Metrics) -> str:
    return json.dumps(asdict(metrics), indent=2, sort_keys=True)


def loads(text: str) -> Metrics:
    data = json.loads(text)
    return Metrics(
        adapter=data["adapter"],
        scenario=data["scenario"],
        runtime=data["runtime"],
        k8s_version=data["k8s_version"],
        iterations=data["iterations"],
        items_mean=data["items_mean"],
        wall=LatencyStats(**data["wall"]),
        per_event=LatencyStats(**data["per_event"]),
        peak_rss_bytes=data["peak_rss_bytes"],
        total_bytes_alloc=data["total_bytes_alloc"],
        total_allocations=data["total_allocations"],
        steady_heap_bytes=data["steady_heap_bytes"],
        cpu_seconds=data["cpu_seconds"],
        asymmetric=data.get("asymmetric", False),
        notes=data.get("notes", []),
    )
