"""Read artifact JSON files and emit a markdown + CSV comparison report."""

from __future__ import annotations

from pathlib import Path

from .metrics import Metrics, loads

_HEADER_TEMPLATE = """\
# Kubex vs kubernetes-asyncio — Benchmark Report

Both libraries run against the same K3s testcontainer (K8s {k8s_version}). kubex uses
the `kubex-k8s-{version_dashed}` model package; `kubernetes-asyncio {k8s_minor}.x` targets the same
server schema — any schema-size differences on the wire are minimised.

Columns:

- `peak_rss_mb` — process peak memory during the measured loop (memray).
- `total_alloc_mb` — cumulative bytes allocated (memray; not net).
- `total_allocs` — number of allocation events (memray).
- `steady_heap_mb` — Python heap after gc.collect() post-loop (tracemalloc).
- `cpu_s` — `time.process_time()` delta across measured iterations.
- `wall_p50_ms` / `wall_p95_ms` / `wall_p99_ms` — per-iteration wall-time
  distribution.
- `evt_p50_us` / `evt_p99_us` — per-event inter-arrival latency (streaming
  scenarios only).

Caveats:

- Memray overhead is <5% but it does intercept allocations, so CPU numbers
  from the same run are slightly inflated. Run once without `--cpu-profile`
  for memory, once with `--cpu-profile --no-memory` for CPU.
- Trio rows exist only for `kubex-httpx-trio`. kubernetes-asyncio does not
  support trio (aiohttp dependency).
- Scenarios marked **asymmetric** compare non-equivalent code paths —
  typically kubex's metadata-only API against kubernetes-asyncio's full list.
  The row is provided for contrast, not as an equal comparison.
"""


def _fmt_bytes_mb(n: int) -> str:
    if n <= 0:
        return "-"
    return f"{n / 1_048_576:.2f}"


def _fmt_ns_ms(n: int | float) -> str:
    if n <= 0:
        return "-"
    return f"{n / 1_000_000:.3f}"


def _fmt_ns_us(n: int | float) -> str:
    if n <= 0:
        return "-"
    return f"{n / 1_000:.2f}"


def _fmt_int(n: int) -> str:
    return str(n) if n else "-"


def _fmt_float(n: float) -> str:
    if n <= 0:
        return "-"
    return f"{n:.3f}"


_ROWS: tuple[tuple[str, str], ...] = (
    ("peak_rss_mb", "peak_rss"),
    ("total_alloc_mb", "total_alloc_bytes"),
    ("total_allocs", "total_allocs"),
    ("steady_heap_mb", "steady_heap"),
    ("cpu_s", "cpu"),
    ("wall_p50_ms", "wall_p50"),
    ("wall_p95_ms", "wall_p95"),
    ("wall_p99_ms", "wall_p99"),
    ("evt_p50_us", "evt_p50"),
    ("evt_p99_us", "evt_p99"),
)


def _render_cell(metric_key: str, m: Metrics) -> str:
    match metric_key:
        case "peak_rss":
            return _fmt_bytes_mb(m.peak_rss_bytes)
        case "total_alloc_bytes":
            return _fmt_bytes_mb(m.total_bytes_alloc)
        case "total_allocs":
            return _fmt_int(m.total_allocations)
        case "steady_heap":
            return _fmt_bytes_mb(m.steady_heap_bytes)
        case "cpu":
            return _fmt_float(m.cpu_seconds)
        case "wall_p50":
            return _fmt_ns_ms(m.wall.p50_ns)
        case "wall_p95":
            return _fmt_ns_ms(m.wall.p95_ns)
        case "wall_p99":
            return _fmt_ns_ms(m.wall.p99_ns)
        case "evt_p50":
            return _fmt_ns_us(m.per_event.p50_ns)
        case "evt_p99":
            return _fmt_ns_us(m.per_event.p99_ns)
    return "-"


def _load_artifacts(artifacts_dir: Path) -> list[Metrics]:
    out: list[Metrics] = []
    for p in sorted(artifacts_dir.glob("*.json")):
        try:
            out.append(loads(p.read_text()))
        except Exception:
            continue
    return out


def _header_note(artifacts: list[Metrics], k8s_version: str | None = None) -> str:
    if k8s_version is None:
        # Fall back to the most common version across artifacts when the caller
        # didn't provide an explicit version (e.g. stand-alone report builds).
        if artifacts:
            from collections import Counter

            k8s_version = Counter(m.k8s_version for m in artifacts).most_common(1)[0][0]
        else:
            k8s_version = "1.33"
    parts = k8s_version.split(".")
    # version_dashed needs only major.minor (e.g. "1-33"), not the patch component.
    version_dashed = (
        "-".join(parts[:2]) if len(parts) >= 2 else k8s_version.replace(".", "-")
    )
    # k8s_minor is the minor portion (e.g. "33" from "1.33.4").
    k8s_minor = parts[1] if len(parts) >= 2 else k8s_version
    return _HEADER_TEMPLATE.format(
        k8s_version=k8s_version,
        version_dashed=version_dashed,
        k8s_minor=k8s_minor,
    )


def _render_markdown(artifacts: list[Metrics], k8s_version: str | None = None) -> str:
    by_scenario: dict[str, list[Metrics]] = {}
    for m in artifacts:
        by_scenario.setdefault(m.scenario, []).append(m)

    lines: list[str] = [_header_note(artifacts, k8s_version)]
    for scenario in sorted(by_scenario):
        rows = sorted(by_scenario[scenario], key=lambda m: m.adapter)
        caveat = " *(asymmetric)*" if any(m.asymmetric for m in rows) else ""
        lines.append(f"\n## `{scenario}`{caveat}\n")
        if rows and rows[0].notes:
            lines.append(f"> {rows[0].notes[0]}\n")
        header = "| metric | " + " | ".join(m.adapter for m in rows) + " |"
        sep = "|" + "---|" * (len(rows) + 1)
        lines.append(header)
        lines.append(sep)
        for display, key in _ROWS:
            cells = " | ".join(_render_cell(key, m) for m in rows)
            lines.append(f"| {display} | {cells} |")
    return "\n".join(lines) + "\n"


def _render_csv(artifacts: list[Metrics]) -> str:
    fields = [
        "adapter",
        "scenario",
        "runtime",
        "k8s_version",
        "iterations",
        "items_mean",
        "peak_rss_bytes",
        "total_bytes_alloc",
        "total_allocations",
        "steady_heap_bytes",
        "cpu_seconds",
        "wall_p50_ns",
        "wall_p95_ns",
        "wall_p99_ns",
        "evt_p50_ns",
        "evt_p99_ns",
        "asymmetric",
    ]
    rows = [",".join(fields)]
    for m in sorted(artifacts, key=lambda x: (x.scenario, x.adapter)):
        rows.append(
            ",".join(
                str(v)
                for v in (
                    m.adapter,
                    m.scenario,
                    m.runtime,
                    m.k8s_version,
                    m.iterations,
                    f"{m.items_mean:.2f}",
                    m.peak_rss_bytes,
                    m.total_bytes_alloc,
                    m.total_allocations,
                    m.steady_heap_bytes,
                    f"{m.cpu_seconds:.6f}",
                    m.wall.p50_ns,
                    m.wall.p95_ns,
                    m.wall.p99_ns,
                    m.per_event.p50_ns,
                    m.per_event.p99_ns,
                    int(m.asymmetric),
                )
            )
        )
    return "\n".join(rows) + "\n"


def build_report(
    artifacts_dir: Path,
    out_md: Path,
    out_csv: Path | None = None,
    k8s_version: str | None = None,
) -> None:
    artifacts = _load_artifacts(artifacts_dir)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(_render_markdown(artifacts, k8s_version))
    if out_csv is not None:
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        out_csv.write_text(_render_csv(artifacts))
