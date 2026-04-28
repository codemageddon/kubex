# Kubex

Kubex is a Kubernetes client library for Python inspired by kube.rs. It is built on top of [Pydantic](https://github.com/pydantic/pydantic) and is async-runtime agnostic.

# Why Kubex?

### Performance

Kubex is dramatically faster than [kubernetes-asyncio](https://github.com/tomplus/kubernetes_asyncio), the most popular async Kubernetes client for Python. Benchmarks against a K3s 1.35 cluster (see `benchmarks/`):

| Scenario | kubernetes-asyncio | kubex (aiohttp) | kubex (httpx) | Speedup |
|---|---|---|---|---|
| Single GET | 60 ms | 6 ms | 28 ms | **10x** |
| List 100 pods | 2,783 ms | 74 ms | 102 ms | **37x** |
| List 500 pods | 14,167 ms | 351 ms | 409 ms | **40x** |
| Watch 50 events | 3,856 ms | 635 ms | 1,914 ms | **6x** |

Kubex also uses **49% less heap memory** and makes **up to 5x fewer allocations**, reducing GC pressure in long-running controllers and operators.

### Fully typed

Every Kubernetes resource is a Pydantic v2 model with proper type annotations — spec fields, status fields, enums, and nested objects are all typed, not `dict[str, Any]`. Combined with `mypy --strict` support, you get IDE autocompletion and compile-time safety instead of runtime KeyErrors.

```python
from kubex.api import Api
from kubex.client import create_client
from kubex.k8s.v1_35.core.v1.pod import Pod

async with await create_client() as client:
    api: Api[Pod] = Api(Pod, client=client)
    pod = await api.get("my-pod", namespace="default")
    # pod.spec, pod.status, pod.metadata are all fully typed
```

### Multi-version Kubernetes support

Kubex ships separate model packages for Kubernetes 1.32 through 1.37. You can depend on exactly the versions you need, or use multiple versions simultaneously — useful when managing clusters at different upgrade stages:

```python
from kubex.k8s.v1_34.apps.v1.deployment import Deployment as Deployment134
from kubex.k8s.v1_35.apps.v1.deployment import Deployment as Deployment135
```

Each package is generated from the official OpenAPI spec, so models always match the wire schema of the target cluster.

### Async-runtime agnostic

Kubex works with both **asyncio** and **trio** (via httpx), with no framework lock-in.

# Completed Features:

* Basic API interface that allows interaction with almost any Kubernetes resources and their methods.
* In-cluster client authorization with token refreshing.
* Basic support for kubeconfig files.
* `httpx` and `aiohttp` as an underlying http-client support.
* `asyncio` and `trio` async runtime support (only `httpx` client is supported for `trio`).
* Comprehensive, fully-typed Kubernetes resource models (1.32–1.37) generated from the OpenAPI spec via a built-in code generator.
> **Experimental — WebSocket subresources.** The `exec`, `attach`, and
> `portforward` APIs described below are still under active development.
> Their public surface (method signatures, accessor shape, session helpers)
> may change in future releases without notice.

* Pod `exec` subresource over WebSocket — one-shot `run()` for collecting output, and `stream()` for interactive sessions with stdin/resize. Both accept `command`, `container`, `stdout`, `stderr`, and `request_timeout`; `run()` takes `stdin` as bytes (or `None` to skip), while `stream()` takes `stdin` and `tty` as bools and exposes `session.stdin.write()`/`close()`, `session.stdout`/`session.stderr` as async iterators, `session.resize(width=, height=)`, and `await session.wait_for_status()` (resolves to a `Status` model when the server emits one on the error channel, or `None` if the connection closes first; correspondingly, `result.exit_code` is `0` on success, the parsed integer for a non-zero exit, or `None` when no recognisable exit information is present — `None` does not imply success). Trio is supported only via the `httpx` client; the `aiohttp` backend is asyncio-only and raises on `connect_websocket()` if used with trio. Requires Kubernetes ≥1.30 (uses the v5 channel protocol; install via `kubex[httpx-ws]` to pull in `httpx-ws` (the plain `kubex[httpx]` extra omits it so non-WebSocket installs stay slim); on Python 3.10 the `exceptiongroup` backport is also installed). See `examples/exec_pod.py`.
* Pod `attach` subresource over WebSocket — `stream()` attaches to an existing container process (stdin/stdout/stderr) without issuing a new command. Exposes the same `StreamSession` interface as `exec` (`session.stdin.write()`/`close()`, `session.stdout`/`session.stderr` as async iterators, `session.resize(width=, height=)`, `await session.wait_for_status()`). Only `stream()` is provided — there is no `run()`. The container must be created with `stdin=True` in its spec for stdin writes to reach the process. Requires `kubex[httpx-ws]` (or `aiohttp`). See `examples/attach_pod.py`.
* Pod `portforward` subresource over WebSocket — two-level API: `api.portforward.forward(name, ports=[…])` yields a `PortForwarder` with one `anyio.abc.ByteStream` per port (`pf.streams[port]`) and a per-port error iterator (`pf.errors[port]`); `api.portforward.listen(name, port_map={remote_port: local_port})` opens local TCP listener sockets and copies bytes bidirectionally between each accepted local connection and a fresh portforward WebSocket session (one session per connection, matching `kubectl port-forward` semantics). Requires `kubex[httpx-ws]` (or `aiohttp`). See `examples/portforward_pod.py`.

```python
from kubex.api import Api
from kubex.client import create_client
from kubex.k8s.v1_35.core.v1.pod import Pod

async with await create_client() as client:
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    result = await api.exec.run("my-pod", command=["echo", "hello"])
    print(result.stdout, result.exit_code)
```

# Planned Features:

* [x] Fine-tuning of timeouts.
* [x] Dynamic API object creation to exclude unsupported methods for resources (requires research for mypy compatibility).
* [x] JsonPatch models.
* [x] Type-safe subresource APIs (logs, scale, status, eviction, ephemeral containers, resize, exec, attach, portforward).
* [x] Additional tests and examples.
* [x] Remaining websocket-based subresources (portforward).
* [ ] Support for OIDC and other authentication extensions.
