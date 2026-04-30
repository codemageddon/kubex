# Kubex vs kubernetes-asyncio benchmarks

This directory holds a runnable performance comparison between **kubex**
(this repo) and **[kubernetes-asyncio](https://github.com/tomplus/kubernetes_asyncio)**
across memory consumption, allocations, CPU time, wall-time, and per-event
latency.

No benchmark numbers are committed — run the suite yourself and read
`report.md` / `report.csv` in this directory afterwards.

## What is compared

| Adapter | Library | HTTP | Runtime |
|---|---|---|---|
| `kubex-httpx-asyncio` | kubex | httpx | asyncio |
| `kubex-httpx-trio` | kubex | httpx | trio |
| `kubex-aiohttp-asyncio` | kubex | aiohttp | asyncio |
| `kubex-metadata-httpx-asyncio` | kubex (`PartialObjectMetadata`) | httpx | asyncio |
| `k8s-asyncio` | kubernetes-asyncio | aiohttp | asyncio |

kubernetes-asyncio does not support trio (its aiohttp backend is
asyncio-only), so trio rows exist only for the kubex-httpx combination.

K8s server is pinned to **v1.35** via the K3s testcontainer image. kubex
uses models from the `kubex-k8s-1-35` workspace package; kubernetes-asyncio
is pinned to `>=35.0.0,<36` — both sides target the same 1.35 wire schema.

## Scenarios

| Scenario | Stresses | Metrics that matter |
|---|---|---|
| `single_get` | hot-path GET | wall latency, CPU, allocations |
| `single_get_metadata` | kubex PartialObjectMetadata GET (asymmetric) | wall latency, allocations |
| `single_create_delete` | JSON serialize + round-trip | wall latency, allocations |
| `list_small` (10) | small deserialize | wall, allocations |
| `list_medium` (100) | mid deserialize | allocations, CPU |
| `list_large` (500) | headline memory scenario | peak RSS, allocations |
| `list_metadata_only` | kubex metadata-only vs k8s-asyncio full list (asymmetric) | peak RSS, allocations |
| `list_namespaces` | cluster-scoped path | wall, allocations |
| `watch_n_events` | streaming + event modelling | per-event latency, allocations/event |
| `stream_logs_n_lines` | chunked text streaming | per-line latency, bytes allocated |

## Install

```bash
uv sync --group benchmark --python 3.14
```

The `benchmark` dependency group adds:

- `kubernetes-asyncio>=35.0.0,<36`
- `memray`, `pytest-memray`, `pyinstrument`
- `pytest-benchmark`
- `kubex-k8s-1-35`
- Both HTTP backends (`httpx`, `aiohttp`) and `trio`

## Run

### Full suite (memory + CPU + latency)

```bash
uv run --group benchmark python -m benchmarks.run \
    --report benchmarks/report.md \
    --csv benchmarks/report.csv
```

This starts a K3s container, seeds 500 pods + 1 log emitter, then spawns
one subprocess per `(adapter, scenario)` pair so the library under test is
the only one loaded in that process. When all pairs are done, artifacts
are aggregated into a markdown + CSV report.

Run only some adapters or scenarios:

```bash
uv run --group benchmark python -m benchmarks.run \
    --adapters kubex-httpx-asyncio k8s-asyncio \
    --scenarios list_large watch_n_events \
    --report benchmarks/report.md
```

Skip memory instrumentation (faster, less jitter for CPU numbers):

```bash
uv run --group benchmark python -m benchmarks.run \
    --no-memory --cpu-profile --report benchmarks/report.md
```

### One pair, one subprocess (debugging)

```bash
uv run --group benchmark python -m benchmarks.runner.harness \
    --adapter kubex-httpx-asyncio \
    --scenario list_large \
    --kubeconfig /path/to/kubeconfig \
    --namespace bench-xyz \
    --runtime asyncio \
    --out /tmp/out.json
```

### Wall-time only (pytest-benchmark)

```bash
uv run --group benchmark pytest benchmarks/test_bench.py --benchmark-only -q
```

This reuses pytest fixtures to bring up K3s + seed pods, then runs each
`(adapter, scenario)` in-process via pytest-benchmark. No memory or
allocation data — use the driver above for that.

### Driver against an existing cluster

If you already have a cluster and kubeconfig, skip the K3s boot:

```bash
uv run --group benchmark python -m benchmarks.runner.driver \
    --kubeconfig /path/to/kubeconfig \
    --namespace bench-existing \
    --artifacts benchmarks/.artifacts \
    --report benchmarks/report.md
```

You must pre-create the namespace and seed pods matching
`--seeded-prefix seed-` and a `log-emitter` pod.

## Measurement details

- Each `(adapter, scenario)` runs in a fresh `python -m benchmarks.runner.harness`
  subprocess so library imports never mix. This matters because the two
  libraries have very different import-time footprints.
- Warm-up: 3 untimed iterations (1 for streaming), then 10 measured (3 for
  streaming). Override with `--warmup-iters` / `--measure-iters`.
- Wall-time: each measured iteration is timed with `time.perf_counter_ns`
  and summarised as mean, stddev, p50, p90, p95, p99, max.
- Per-event latency: for `watch_n_events` and `stream_logs_n_lines`,
  adapters record `perf_counter_ns` on every event received and report
  inter-arrival deltas. Summarised identically to wall-time.
- Memory: `memray.Tracker(native_traces=False)` wraps the measured loop.
  `memray.FileReader(...).metadata` supplies peak RSS, total bytes
  allocated, and allocation count.
- Steady heap: `gc.collect()` + `tracemalloc.get_traced_memory()` after the
  loop, as a sanity check against memray's peak.
- CPU: optional `--cpu-profile` enables `pyinstrument`. Output is a
  `.speedscope.json` sidecar per pair, readable at
  [speedscope.app](https://www.speedscope.app/). `cpu_seconds` in the
  report comes from `time.process_time()` over the measured loop (always
  captured, cheap).

## Known caveats

- **Linux-only memory numbers.** memray's `native_traces=False` works on
  macOS but peak-RSS accounting differs between platforms. Report numbers
  from runs on Linux.
- **pyinstrument perturbs wall-time.** It wraps Python frames; wall-time
  numbers collected with `--cpu-profile` are slightly inflated. For a
  clean wall-time pass, omit `--cpu-profile`.
- **Asymmetric scenarios.** `list_metadata_only` and `single_get_metadata`
  compare non-equivalent code paths. kubernetes-asyncio has no
  `PartialObjectMetadata` equivalent, so its rows on those scenarios show
  a *full* list/get for reference only. The report flags these rows.
- **Watch event model.** kubex yields a `WatchEvent` wrapping a Pydantic
  resource; kubernetes-asyncio yields a dict with a deserialised `V1Pod`.
  Both do meaningful work per event; the report captures that difference
  rather than hiding it.
- **K3s boot.** ~20s per session. Cached by fixture scope, so this cost
  is paid once per `python -m benchmarks.run` invocation.
- **Cluster write latency bounds wall-time.** For mutation scenarios
  (`single_create_delete`, `watch_n_events`), the K3s API server is the
  common bottleneck — differences between adapters show up mainly in CPU
  + allocations, not wall-time.
