# Portforward

The `portforward` subresource opens a WebSocket tunnel to the kubelet and forwards TCP traffic between your local machine (or in-process code) and a port inside a running Pod.

!!! warning "Beta / experimental"
    The portforward WebSocket implementation is functional and tested against K3S, but the underlying
    channel-protocol layer is relatively new. The API may change between minor releases.

## Availability

Only resources that implement the `HasPortForward` marker interface expose `api.portforward`. In practice this means `Pod`. Accessing `api.portforward` on any other resource type raises `NotImplementedError` at runtime and resolves to `SubresourceNotAvailable` for the type-checker.

## Installation requirement

Portforward uses a WebSocket upgrade. You need **one** of:

- `kubex[httpx-ws]` — httpx client with the `httpx-ws` WebSocket extension
- `kubex[aiohttp]` — aiohttp client with built-in WebSocket support

```bash
pip install "kubex[httpx-ws]"
# or
pip install "kubex[aiohttp]"
```

## Two-level API

Kubex provides two levels of port-forwarding:

| Level | Method | Use case |
|-------|--------|----------|
| Low-level | `api.portforward.forward()` | Python code reads/writes bytes directly — no local TCP socket |
| High-level | `api.portforward.listen()` | Binds a local TCP port; any process can connect (kubectl-style) |

## Low-level: `forward()`

`api.portforward.forward()` is an async context manager that yields a `PortForwarder`. The `PortForwarder` exposes per-port `ByteStream` objects for direct byte-level access, plus per-port error iterators.

```python
from typing import cast

import anyio

from kubex.api import Api
from kubex.client import create_client
from kubex.k8s.v1_35.core.v1.container import Container
from kubex.k8s.v1_35.core.v1.container_port import ContainerPort
from kubex.k8s.v1_35.core.v1.pod import Pod
from kubex.k8s.v1_35.core.v1.pod_spec import PodSpec
from kubex_core.models.metadata import ObjectMetadata

HTTP_REQUEST = b"GET / HTTP/1.0\r\nHost: localhost\r\n\r\n"


async def main() -> None:
    client = await create_client()
    async with client:
        api: Api[Pod] = Api(Pod, client=client, namespace="default")
        pod = await api.create(
            Pod(
                metadata=ObjectMetadata(generate_name="example-portforward-"),
                spec=PodSpec(
                    containers=[
                        Container(
                            name="main",
                            image="nginx:1.25",
                            ports=[ContainerPort(container_port=80)],
                        )
                    ]
                ),
            ),
        )
        pod_name = cast(str, pod.metadata.name)
        try:
            async with api.portforward.forward(pod_name, ports=[80]) as pf:
                stream = pf.streams[80]
                with anyio.fail_after(10):
                    await stream.send(HTTP_REQUEST)
                    buf = bytearray()
                    while True:
                        try:
                            chunk = await stream.receive()
                            buf.extend(chunk)
                            if b"\r\n\r\n" in buf:
                                break
                        except anyio.EndOfStream:
                            break
            print(buf.decode(errors="replace").split("\r\n")[0])
        finally:
            await api.delete(pod_name)
```

### PortForwarder

`PortForwarder` has two mappings:

| Attribute | Type | Description |
|-----------|------|-------------|
| `streams` | `Mapping[int, PortForwardStream]` | One `anyio.abc.ByteStream` per forwarded port |
| `errors` | `Mapping[int, MemoryObjectReceiveStream[str]]` | Per-port kubelet error messages (typically empty on success) |

`PortForwardStream` is an `anyio.abc.ByteStream`, so you can use `send()` and `receive()` on it directly.

### Forwarding multiple ports

Pass multiple ports to `forward()`:

```python
async with api.portforward.forward(pod_name, ports=[80, 443]) as pf:
    http_stream = pf.streams[80]
    https_stream = pf.streams[443]
    ...
```

## High-level: `listen()`

`api.portforward.listen()` binds real local TCP sockets and proxies connections kubectl-style. Each accepted TCP connection gets its own WebSocket session. Use this when an external process (browser, `curl`, `psql`) needs to reach the pod.

```python
from typing import cast

import anyio

from kubex.api import Api
from kubex.client import create_client
from kubex.k8s.v1_35.core.v1.container import Container
from kubex.k8s.v1_35.core.v1.container_port import ContainerPort
from kubex.k8s.v1_35.core.v1.pod import Pod
from kubex.k8s.v1_35.core.v1.pod_spec import PodSpec
from kubex_core.models.metadata import ObjectMetadata

LOCAL_PORT = 18080
HTTP_REQUEST = b"GET / HTTP/1.0\r\nHost: localhost\r\n\r\n"


async def main() -> None:
    client = await create_client()
    async with client:
        api: Api[Pod] = Api(Pod, client=client, namespace="default")
        pod = await api.create(
            Pod(
                metadata=ObjectMetadata(generate_name="example-portforward-"),
                spec=PodSpec(
                    containers=[
                        Container(
                            name="main",
                            image="nginx:1.25",
                            ports=[ContainerPort(container_port=80)],
                        )
                    ]
                ),
            ),
        )
        pod_name = cast(str, pod.metadata.name)
        try:
            async with api.portforward.listen(pod_name, port_map={80: LOCAL_PORT}):
                async with await anyio.connect_tcp("127.0.0.1", LOCAL_PORT) as conn:
                    with anyio.fail_after(10):
                        await conn.send(HTTP_REQUEST)
                        buf = bytearray()
                        while True:
                            try:
                                chunk = await conn.receive()
                                buf.extend(chunk)
                                if b"\r\n\r\n" in buf:
                                    break
                            except anyio.EndOfStream:
                                break
            print(buf.decode(errors="replace").split("\r\n")[0])
        finally:
            await api.delete(pod_name)
```

### Port map

`listen()` takes a `port_map` dict mapping remote port (inside the pod) to local port (on the host):

```python
# Remote 5432 (postgres) → local 15432
async with api.portforward.listen(pod_name, port_map={5432: 15432}):
    # connect with: psql -h 127.0.0.1 -p 15432 ...
    ...
```

### Error logging

`listen()` logs kubelet error frames via the `kubex.portforward` logger at `WARNING` level. Configure Python logging to capture them:

```python
import logging
logging.basicConfig(level=logging.WARNING)
```

## `forward()` vs `listen()` decision guide

- **Only Python code needs to talk to the pod?** Use `forward()`. It avoids binding a host socket and keeps traffic in-process.
- **External tools need the port?** Use `listen()`. It behaves exactly like `kubectl port-forward`.
- **Multiple concurrent connections to the same pod port?** Use `listen()` — each accepted connection gets its own WebSocket session automatically.

## Advanced: port-prefix protocol

For readers interested in the wire-level detail: the kubelet prepends a 2-byte little-endian port number to the **first** frame on each channel (data and error independently). Kubex validates and strips this prefix transparently. Subsequent frames carry raw bytes — the channel ID alone addresses the kubelet. Outbound writes from Kubex carry no port prefix.
