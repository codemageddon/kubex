# Clients & Runtimes

Kubex supports two HTTP client backends and two async runtimes. This page explains the trade-offs so you can pick the right combination for your use case.

## HTTP clients

| Client | Install | WebSocket | Trio |
|---|---|---|---|
| `aiohttp` | `kubex[aiohttp]` | built-in | no |
| `httpx` | `kubex[httpx]` | requires `kubex[httpx-ws]` | yes |

### aiohttp

`aiohttp` is the faster backend for asyncio workloads. Benchmarks show it is consistently **~10× faster than `kubernetes-asyncio`** on single-request paths and **~40× faster** on large list/deserialise paths, and it is faster than the httpx backend on most list and watch scenarios. It has built-in WebSocket support, so `exec`, `attach`, and `portforward` work without any extra dependencies.

```bash
pip install "kubex[aiohttp,k8s-1.35]"
```

### httpx

`httpx` is the recommended backend when you need **trio** support, or when you prefer the httpx ecosystem. It also supports WebSocket via the `httpx-ws` extra.

```bash
# asyncio only, no WebSocket
pip install "kubex[httpx,k8s-1.35]"

# asyncio + WebSocket (exec, attach, portforward)
pip install "kubex[httpx-ws,k8s-1.35]"
```

The plain `kubex[httpx]` extra intentionally omits `httpx-ws` so that non-WebSocket installs stay slim. If you call `api.exec.run()` or `api.attach.stream()` without `httpx-ws` installed, a `ConfgiurationError` is raised at runtime.

### Auto-detection

`create_client()` picks a backend automatically. It tries `aiohttp` first, then `httpx`, and raises `ImportError` if neither is installed:

```python
from kubex.client import create_client

async with await create_client() as client:
    ...
```

To force a specific backend, pass the `client_class` parameter:

```python
from kubex.client import create_client, ClientChoise

async with await create_client(client_class=ClientChoise.HTTPX) as client:
    ...
```

## Async runtimes

| Runtime | aiohttp | httpx |
|---|---|---|
| asyncio | yes | yes |
| trio | no | yes |

### asyncio

Both backends work with asyncio. This is the default for most Python applications and all CI environments.

### trio

Trio is supported only with the `httpx` client. The `aiohttp` backend relies on asyncio internals and raises an error if used with trio.

```python
import trio
from kubex.api import Api
from kubex.client import create_client, ClientChoise
from kubex.k8s.v1_35.core.v1.pod import Pod

async def main():
    async with await create_client(client_class=ClientChoise.HTTPX) as client:
        api: Api[Pod] = Api(Pod, client=client, namespace="default")
        pod = await api.get("my-pod")
        print(pod.metadata.name)

trio.run(main)
```

## WebSocket support matrix

WebSocket-based subresources (`exec`, `attach`, `portforward`) require a client that supports WebSocket upgrades:

| Backend | WebSocket extra needed | Trio WebSocket |
|---|---|---|
| aiohttp | none (built-in) | no |
| httpx | `kubex[httpx-ws]` | yes |

## Choosing a combination

For most applications running on asyncio, `aiohttp` is the best choice — lowest latency, fewest dependencies, built-in WebSocket.

Use `httpx` when:
- Your application uses trio.
- You already use httpx elsewhere and want a consistent HTTP layer.
- You need the httpx middleware / transport ecosystem (e.g., custom retry or proxy transports).
