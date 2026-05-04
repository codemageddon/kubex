# Benchmarks

Kubex is dramatically faster than [kubernetes-asyncio](https://github.com/tomplus/kubernetes_asyncio), the most widely used async Kubernetes client for Python.

## Summary

Benchmarks run against a K3s 1.35.4 cluster (K3s testcontainer, same hardware, same server):

| Scenario | kubernetes-asyncio | kubex (aiohttp) | kubex (httpx) | Speedup |
|---|---|---|---|---|
| Single GET | 61 ms | 6 ms | 26 ms | **10×** |
| List 100 pods | 2,813 ms | 73 ms | 102 ms | **38×** |
| List 500 pods | 14,441 ms | 351 ms | 410 ms | **41×** |
| Watch 50 events | 3,957 ms | 562 ms | 1,764 ms | **7×** |

Kubex also uses **~47% less heap memory** and makes **up to ~5× fewer allocations**, reducing GC pressure in long-running controllers and operators.

## Detailed results

Results below are from `benchmarks/report.md` in the repository. All numbers use a K3s 1.35.4 testcontainer. See the caveats section for measurement details.

### Single GET

> Single pod GET against a pre-seeded namespace.

| metric | k8s-asyncio | kubex-aiohttp | kubex-httpx | kubex-httpx-trio |
|---|---|---|---|---|
| wall p50 (ms) | 60.8 | 5.7 | 25.6 | 27.0 |
| wall p95 (ms) | 66.9 | 7.4 | 26.9 | 27.7 |
| steady heap (MB) | 55.4 | 27.9 | 31.7 | 30.2 |
| total allocations | 15,517,716 | 4,152,111 | 3,226,073 | 3,268,915 |

### List 100 pods

> List ~100 pods in bench namespace.

| metric | k8s-asyncio | kubex-aiohttp | kubex-httpx | kubex-httpx-trio |
|---|---|---|---|---|
| wall p50 (ms) | 2,813 | 73 | 102 | 100 |
| wall p95 (ms) | 2,920 | 79 | 107 | 109 |
| steady heap (MB) | 52.1 | 27.5 | 31.7 | 30.2 |
| total allocations | 7,934,267 | 3,619,184 | 3,936,894 | 3,870,615 |

### List 500 pods

> List ~500 pods in bench namespace.

| metric | k8s-asyncio | kubex-aiohttp | kubex-httpx | kubex-httpx-trio |
|---|---|---|---|---|
| wall p50 (ms) | 14,441 | 351 | 410 | 390 |
| wall p95 (ms) | 14,574 | 618 | 533 | 456 |
| steady heap (MB) | 52.2 | 27.6 | 31.8 | 30.3 |
| total allocations | 29,948,177 | 6,506,349 | 6,940,526 | 6,893,850 |

### Watch 50 events

> Receive N watch events driven by a sibling create/delete burst.

| metric | k8s-asyncio | kubex-aiohttp | kubex-httpx | kubex-httpx-trio |
|---|---|---|---|---|
| wall p50 (ms) | 3,957 | 562 | 1,764 | 1,863 |
| evt p50 (µs) | 24,069 | 1,611 | 3,581 | 4,729 |
| evt p99 (µs) | 56,655 | 9,163 | 5,855 | 15,563 |
| steady heap (MB) | 52.2 | 27.6 | 31.7 | 30.2 |
| total allocations | 4,977,137 | 3,472,840 | 4,685,643 | 4,714,213 |

### PartialObjectMetadata (asymmetric)

> Kubex metadata-only list vs kubernetes-asyncio full list. These are asymmetric — kubernetes-asyncio has no metadata-only equivalent, so its numbers reflect a full object list for contrast. The metadata adapter uses the aiohttp backend so the comparison isolates the `?as=PartialObjectMetadata` saving from any HTTP-stack speed difference.

| metric | k8s-asyncio (full list, 100 pods) | kubex-metadata-aiohttp |
|---|---|---|
| wall p50 (ms) | 2,813 | 14.0 |
| wall p95 (ms) | 3,274 | 15.6 |
| steady heap (MB) | 52.1 | 27.6 |
| total allocations | 7,934,232 | 3,061,371 |

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
