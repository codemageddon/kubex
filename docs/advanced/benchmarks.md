# Benchmarks

Kubex is dramatically faster than [kubernetes-asyncio](https://github.com/tomplus/kubernetes_asyncio), the most widely used async Kubernetes client for Python.

## Summary

Benchmarks run against a K3s 1.35 cluster (K3s testcontainer, same hardware, same server):

| Scenario | kubernetes-asyncio | kubex (aiohttp) | kubex (httpx) | Speedup |
|---|---|---|---|---|
| Single GET | 68 ms | 7 ms | 26 ms | **10×** |
| List 100 pods | 14,648 ms | 346 ms | 415 ms | **42×** |
| List 500 pods | 14,674 ms | 348 ms | 412 ms | **42×** |
| Watch 50 events | 3,868 ms | 1,200 ms | 1,898 ms | **3×** |

Kubex also uses **49% less heap memory** and makes **up to 5× fewer allocations**, reducing GC pressure in long-running controllers and operators.

## Detailed results

Results below are from `benchmarks/report.md` in the repository. All numbers use a K3s 1.35 testcontainer on Linux. See the caveats section for measurement details.

### Single GET

> Single pod GET against a pre-seeded namespace.

| metric | k8s-asyncio | kubex-aiohttp | kubex-httpx | kubex-httpx-trio |
|---|---|---|---|---|
| wall p50 (ms) | 67.6 | 6.7 | 26.5 | 27.0 |
| wall p95 (ms) | 70.3 | 7.4 | 32.3 | 28.8 |
| steady heap (MB) | 50.5 | 26.6 | 30.7 | 29.2 |
| total allocations | 2,674,844 | 2,755,851 | 3,042,188 | 2,971,923 |

### List 100 pods

> List ~100 pods in bench namespace.

| metric | k8s-asyncio | kubex-aiohttp | kubex-httpx | kubex-httpx-trio |
|---|---|---|---|---|
| wall p50 (ms) | 14,648 | 346 | 415 | 388 |
| wall p95 (ms) | 14,663 | 358 | 428 | 397 |
| steady heap (MB) | 50.6 | 26.7 | 30.8 | 29.3 |
| total allocations | 31,050,288 | 6,370,304 | 6,785,110 | 6,771,325 |

### List 500 pods

> List ~500 pods in bench namespace.

| metric | k8s-asyncio | kubex-aiohttp | kubex-httpx | kubex-httpx-trio |
|---|---|---|---|---|
| wall p50 (ms) | 14,674 | 348 | 412 | 390 |
| wall p95 (ms) | 14,727 | 358 | 433 | 397 |
| steady heap (MB) | 50.6 | 26.7 | 30.8 | 29.3 |
| total allocations | 31,048,536 | 6,370,472 | 6,795,165 | 6,771,446 |

### Watch 50 events

> Receive N watch events driven by a sibling create/delete burst.

| metric | k8s-asyncio | kubex-aiohttp | kubex-httpx | kubex-httpx-trio |
|---|---|---|---|---|
| wall p50 (ms) | 3,868 | 1,200 | 1,898 | 1,996 |
| evt p50 (µs) | 23,388 | 1,527 | 3,562 | 4,580 |
| evt p99 (µs) | 61,776 | 9,305 | 6,194 | 15,684 |
| steady heap (MB) | 50.6 | 26.6 | 30.7 | 29.3 |
| total allocations | 4,924,497 | 3,381,830 | 4,517,750 | 4,547,164 |

### PartialObjectMetadata (asymmetric)

> Kubex metadata-only list vs kubernetes-asyncio full list. These are asymmetric — kubernetes-asyncio has no metadata-only equivalent, so its numbers reflect a full object list for contrast.

| metric | k8s-asyncio (full list) | kubex-metadata-httpx |
|---|---|---|
| wall p50 (ms) | 14,553 | 75 |
| steady heap (MB) | 50.5 | 30.8 |
| total allocations | 31,046,884 | 3,706,741 |

## Why the gap is so large

kubernetes-asyncio deserializes every response into Python dicts, validates fields with hand-written code, and constructs `V1*` objects via keyword arguments — an extremely allocation-heavy path. Kubex uses Pydantic v2's Rust-backed validator, which parses JSON directly into typed Python objects in a single pass with far fewer intermediate allocations.

The list scenario magnifies this: deserializing 500 pods iterates the kubernetes-asyncio path 500 times. Kubex parses the entire list response in one Pydantic call.

## Reproducing the benchmarks

Requirements: Docker (for the K3s testcontainer).

```bash
# Install the benchmark dependency group
uv sync --group benchmark --python 3.13

# Run the full suite (starts K3s, seeds pods, measures)
uv run --group benchmark python -m benchmarks.run \
    --report benchmarks/report.md \
    --csv benchmarks/report.csv
```

Run only specific adapters or scenarios:

```bash
uv run --group benchmark python -m benchmarks.run \
    --adapters kubex-aiohttp-asyncio k8s-asyncio \
    --scenarios single_get list_large \
    --report benchmarks/report.md
```

Skip memory instrumentation for faster CPU-focused numbers:

```bash
uv run --group benchmark python -m benchmarks.run \
    --no-memory --cpu-profile --report benchmarks/report.md
```

## Measurement methodology

- Each `(adapter, scenario)` runs in a **fresh subprocess** so library imports never mix (the two libraries have very different import-time footprints).
- Warm-up: 3 untimed iterations (1 for streaming scenarios), then 10 measured (3 for streaming).
- Wall-time: `time.perf_counter_ns` per iteration; reported as p50 / p95 / p99.
- Memory: `memray.Tracker` wraps the measured loop; provides peak RSS, total bytes allocated, and allocation count.
- Steady heap: `gc.collect()` + `tracemalloc.get_traced_memory()` after the loop.
- CPU: `time.process_time()` delta over the measured loop (always captured, cheap).

## Caveats

- Memory numbers are Linux-only — peak RSS accounting differs on macOS.
- `--cpu-profile` (pyinstrument) slightly inflates wall-time. For clean wall-time, omit it.
- Asymmetric scenarios (`list_metadata_only`, `single_get_metadata`) compare non-equivalent code paths — kubernetes-asyncio rows on those scenarios show a full list/get for reference only.
- K3s boot takes ~20s per session; this cost is paid once per `python -m benchmarks.run` invocation.
- For mutation scenarios (`single_create_delete`, `watch_n_events`), the K3s API server is the common bottleneck — differences between adapters appear mainly in CPU + allocations, not wall-time.
