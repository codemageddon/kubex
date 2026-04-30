# Attach

The `attach` subresource opens a WebSocket connection to the kubelet and attaches to a **running** container process — without starting a new command.

!!! warning "Beta / experimental"
    The attach WebSocket implementation is functional and tested against K3S, but the underlying
    channel-protocol layer is relatively new. The API may change between minor releases.
    Requires Kubernetes ≥ 1.30 (v5 channel protocol).

## Exec vs Attach

| | `exec` | `attach` |
|-|--------|---------|
| Starts a new command | yes | no |
| Connects to | new process | existing container entrypoint |
| `run()` (one-shot) | yes | no |
| `stream()` (interactive) | yes | yes |

Use `attach` when you want to connect to a container that was started with `stdin: true` in its spec — for example, an interactive REPL, a legacy daemon that reads from stdin, or a container designed for interactive debugging. Use `exec` to run a one-off command.

## Installation requirement

Attach uses a WebSocket upgrade. You need **one** of:

- `kubex[httpx-ws]` — httpx client with the `httpx-ws` WebSocket extension
- `kubex[aiohttp]` — aiohttp client with built-in WebSocket support

```bash
pip install "kubex[httpx-ws]"
# or
pip install "kubex[aiohttp]"
```

## Availability

Only resources that implement the `HasAttach` marker interface expose `api.attach`. In practice this means `Pod`. Accessing `api.attach` on any other resource type raises `NotImplementedError` at runtime and resolves to `SubresourceNotAvailable` for the type-checker.

## Container requirement

The target container must have been created with `stdin: true` in its spec. If the container was not configured to accept stdin, attaching will succeed at the protocol level but your writes will be discarded.

## Attaching to a container

`api.attach.stream()` is an async context manager that returns a `StreamSession` — the same type used by `api.exec.stream()`.

```python
from typing import cast

import anyio

from kubex.api import Api
from kubex.client import create_client
from kubex.k8s.v1_35.core.v1.container import Container
from kubex.k8s.v1_35.core.v1.pod import Pod
from kubex.k8s.v1_35.core.v1.pod_spec import PodSpec
from kubex_core.models.metadata import ObjectMetadata


async def main() -> None:
    client = await create_client()
    async with client:
        api: Api[Pod] = Api(Pod, client=client, namespace="default")
        pod = await api.create(
            Pod(
                metadata=ObjectMetadata(generate_name="example-attach-"),
                spec=PodSpec(
                    containers=[
                        Container(
                            name="main",
                            image="busybox:1.36",
                            command=[
                                "sh",
                                "-c",
                                'while IFS= read -r line; do printf "echo: %s\\n" "$line"; done',
                            ],
                            stdin=True,
                        )
                    ]
                ),
            ),
        )
        pod_name = cast(str, pod.metadata.name)
        try:
            async with api.attach.stream(
                pod_name,
                stdin=True,
                stdout=True,
            ) as session:
                await session.stdin.write(b"hello\n")

                buf = bytearray()
                with anyio.fail_after(10):
                    async for chunk in session.stdout:
                        buf.extend(chunk)
                        if b"echo: hello" in buf:
                            break
                print("attach output:", bytes(buf).decode(errors="replace"))

                await session.close_stdin()
        finally:
            await api.delete(pod_name)
```

### StreamSession API

`api.attach.stream()` returns the same `StreamSession` as `api.exec.stream()`:

| Member | Type | Description |
|--------|------|-------------|
| `stdin` | writer | Call `await session.stdin.write(data)` to send bytes to the container |
| `stdout` | `MemoryObjectReceiveStream[bytes]` | Async iterable yielding stdout chunks |
| `stderr` | `MemoryObjectReceiveStream[bytes]` | Async iterable yielding stderr chunks |
| `resize(width, height)` | coroutine | Send a terminal resize event |
| `close_stdin()` | coroutine | Half-close the stdin channel (idempotent) |
| `wait_for_status()` | coroutine | Await the final status frame; returns `Status | None` |

### TTY mode and stderr

When `tty=True`, the kubelet merges stderr into stdout. `session.stderr` closes immediately. Read only `session.stdout` when `tty=True`.

### `stream()` options

| Option | Type | Description |
|--------|------|-------------|
| `stdin` | `bool` | Whether to attach to the stdin channel |
| `stdout` | `bool` | Whether to attach to the stdout channel (default `True`) |
| `stderr` | `bool` | Whether to attach to the stderr channel |
| `tty` | `bool` | Whether the container stdin is a TTY |
| `container` | `str | None` | Container name — required for multi-container pods |
| `namespace` | `str | None | ...` | Override the `Api` instance namespace |
| `request_timeout` | `Timeout | float | None | ...` | Override the client-level timeout |

## Exiting early

Exiting the `async with` block cancels the read loop before the WebSocket closes. You can break out of the attach session at any point without deadlocking.
