# Exec

The `exec` subresource opens a WebSocket connection to the kubelet and runs a command inside a running container.

!!! warning "Beta / experimental"
    The exec WebSocket implementation is functional and tested against K3S, but the underlying
    channel-protocol layer is relatively new. The API may change between minor releases.
    Requires Kubernetes ≥ 1.30 (v5 channel protocol).

## Installation requirement

Exec (and attach) use a WebSocket upgrade. You need **one** of:

- `kubex[httpx-ws]` — httpx client with the `httpx-ws` WebSocket extension
- `kubex[aiohttp]` — aiohttp client with built-in WebSocket support

```bash
pip install "kubex[httpx-ws]"
# or
pip install "kubex[aiohttp]"
```

Missing the WebSocket dependency raises `ConfigurationError` at call time, not at import time.

## Availability

Only resources that implement the `HasExec` marker interface expose `api.exec`. In practice this means `Pod`. Accessing `api.exec` on any other resource type raises `NotImplementedError` at runtime and resolves to `SubresourceNotAvailable` for the type-checker.

```python
from kubex.k8s.v1_35.core.v1.pod import Pod

pod_api.exec.run(...)  # OK: Pod has HasExec

from kubex.k8s.v1_35.apps.v1.deployment import Deployment

deploy_api.exec.run(...)  # type error + runtime NotImplementedError
```

## One-shot execution

`api.exec.run()` collects all output and waits for the command to finish, then returns an `ExecResult`.

```python
from typing import cast

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
                metadata=ObjectMetadata(generate_name="example-exec-"),
                spec=PodSpec(
                    containers=[
                        Container(
                            name="main",
                            image="busybox:1.36",
                            command=["sleep", "3600"],
                        )
                    ]
                ),
            ),
        )
        pod_name = cast(str, pod.metadata.name)
        try:
            result = await api.exec.run(pod_name, command=["ls", "-la", "/"])
            print(f"exit code: {result.exit_code}")
            print(result.stdout.decode())
            if result.stderr:
                print("stderr:", result.stderr.decode())
        finally:
            await api.delete(pod_name)
```

### ExecResult

`api.exec.run()` returns an `ExecResult` with:

| Attribute | Type | Description |
|-----------|------|-------------|
| `stdout` | `bytes` | All stdout output collected from the command |
| `stderr` | `bytes` | All stderr output collected from the command |
| `status` | `Status | None` | The final `Status` the server sent on the error channel |
| `exit_code` | `int | None` | Exit code of the command — see semantics below |
| `raise_for_status()` | method | Raise `ExecError` unless the command succeeded; returns the result otherwise |

### Exit code semantics

`ExecResult.exit_code` has three possible states:

- `0` — the command exited with `Status.status == "Success"`
- an `int` — the non-zero exit code parsed from `status.details.causes` (where `reason == "ExitCode"`)
- `None` — the status frame was missing or carried no recognisable exit information

**`None` does not imply success.** If the WebSocket connection closed unexpectedly before a status frame arrived, `exit_code` is `None`. So is a command that could not start at all (e.g. a missing binary): the server reports `status="Failure"` without an exit code, so `if result.exit_code:` would wrongly treat it as success.

### Checking for success

`ExecResult.raise_for_status()` raises `ExecError` (a `KubexClientException` subclass) unless the
server reported `Success`, covering non-zero exits, commands that failed to start, and a missing
status. The exception message is the server's `Status.message`; `exc.result`, `exc.status` and
`exc.exit_code` carry the details. It returns the result, so it chains:

```python
from kubex.api._exec import ExecError

try:
    result = (await api.exec.run(pod_name, command=["cat", "/etc/hostname"])).raise_for_status()
    print(result.stdout.decode())
except ExecError as e:
    print(f"command failed (exit code {e.exit_code}): {e}")
```

### Passing stdin to `run()`

Pass `stdin=None` (default) to skip opening a stdin channel entirely. Pass `stdin=b""` to open the channel, write zero bytes, and immediately close it — useful for commands that check whether stdin is a terminal:

```python
result = await api.exec.run(pod_name, command=["cat", "/etc/hostname"], stdin=None)
```

`stdin` is sent in frames of at most 32 KiB (the API server rejects oversized WebSocket messages),
then half-closed. If sending it fails part-way — typically because the command exited without
reading all of its input — the error is logged (`kubex.exec` logger, `DEBUG`) and `run()` still
returns whatever status the server reported.

### `run()` options

| Option | Type | Description |
|--------|------|-------------|
| `command` | `list[str]` | Command and arguments to execute |
| `container` | `str | None` | Container name — required when the Pod has more than one container |
| `stdin` | `bytes | None` | Bytes to write to stdin, or `None` to skip the stdin channel |
| `stdout` | `bool` | Capture stdout (default `True`) |
| `stderr` | `bool` | Capture stderr (default `True`) |
| `namespace` | `str | None | ...` | Override the `Api` instance namespace for this call |
| `request_timeout` | `Timeout | float | None | ...` | Override the client-level timeout for this call |

## Interactive streaming

`api.exec.stream()` is an async context manager that opens a bidirectional WebSocket session and returns a `StreamSession`. Use it for interactive shells, long-running commands with live output, or anything that needs to resize the terminal.

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
                metadata=ObjectMetadata(generate_name="example-exec-"),
                spec=PodSpec(
                    containers=[
                        Container(
                            name="main",
                            image="busybox:1.36",
                            command=["sleep", "3600"],
                        )
                    ]
                ),
            ),
        )
        pod_name = cast(str, pod.metadata.name)
        try:
            async with api.exec.stream(
                pod_name,
                command=["sh"],
                stdin=True,
                stdout=True,
                stderr=True,
                tty=True,
            ) as session:
                await session.resize(width=120, height=40)
                await session.stdin.write(b"echo MARK-$$\n")

                buf = bytearray()
                with anyio.fail_after(5):
                    async for chunk in session.stdout:
                        buf.extend(chunk)
                        if b"MARK-" in buf:
                            break
                print("interactive output:", bytes(buf).decode(errors="replace"))

                await session.stdin.write(b"exit 0\n")
                await session.close_stdin()

                status = await session.wait_for_status()
                print(f"session status: {status.status if status else 'unknown'}")
        finally:
            await api.delete(pod_name)
```

### StreamSession API

| Member | Type | Description |
|--------|------|-------------|
| `stdin` | writer | Call `await session.stdin.write(data)` to send bytes to the container |
| `stdout` | `MemoryObjectReceiveStream[bytes]` | Async iterable yielding stdout chunks |
| `stderr` | `MemoryObjectReceiveStream[bytes]` | Async iterable yielding stderr chunks |
| `resize(width, height)` | coroutine | Send a terminal resize event |
| `close_stdin()` | coroutine | Half-close the stdin channel (idempotent) |
| `wait_for_status()` | coroutine | Await the final status; returns `Status | None` (`None` if the server closed without one) |

`stdin.write()` sends large payloads in frames of at most 32 KiB; frames of one write are never
interleaved with another write. Calling `stdin.write()`, `resize()` or `close_stdin()` after the
session has ended raises `KubexClientException`. `stdout_truncated`/`stderr_truncated` are
deprecated and always `False`.

### Reading output: backpressure

Output is never dropped. `stdout` and `stderr` each queue up to 128 frames; when a queue is full,
kubex stops reading from the WebSocket until you consume more (the same backpressure `kubectl`
and client-go apply), which in turn pauses the remote process once its pipes fill.

Because both channels — and the final status — share one WebSocket, **a channel you don't read
stalls the others**: a consumer that only iterates `stdout` while the command floods `stderr`
will stop receiving stdout once the stderr queue fills, and `wait_for_status()` waits behind
unread output too. For every channel you enable, do one of:

- read it concurrently with the others (e.g. one task per channel),
- disable it in the request (`stderr=False`), or
- close it to discard its data: `session.stderr.close()`.

```python
import sys

import anyio

async with api.exec.stream(pod_name, command=["sh", "-c", "./run-job.sh"]) as session:

    async def drain_stderr() -> None:
        async for chunk in session.stderr:
            sys.stderr.buffer.write(chunk)

    async with anyio.create_task_group() as tg:
        tg.start_soon(drain_stderr)
        async for chunk in session.stdout:
            sys.stdout.buffer.write(chunk)
    status = await session.wait_for_status()
```

Leaving the `async with` block (or cancelling the surrounding scope) always tears the session
down promptly, even while kubex is waiting on a full queue.

### TTY mode and stderr

When `tty=True`, the kubelet merges stderr into stdout — only the stdout channel is opened. `session.stderr` will close immediately. Always read only `session.stdout` when `tty=True`.

### Exiting a stream early

Exiting the `async with api.exec.stream(...)` block cancels the read loop before the WebSocket is closed. You can break out early (for example, once you have seen the marker you were waiting for) without deadlocking even when the server is still holding the connection open.

### `stream()` options

| Option | Type | Description |
|--------|------|-------------|
| `command` | `list[str]` | Command and arguments to execute |
| `stdin` | `bool` | Whether to open the stdin channel |
| `stdout` | `bool` | Whether to open the stdout channel (default `True`) |
| `stderr` | `bool` | Whether to open the stderr channel |
| `tty` | `bool` | Whether to allocate a pseudo-terminal |
| `container` | `str | None` | Container name — required for multi-container pods |
| `namespace` | `str | None | ...` | Override the `Api` instance namespace |
| `request_timeout` | `Timeout | float | None | ...` | Override the client-level timeout |

## Error handling

WebSocket handshake failures, abnormal close codes, and per-call timeouts surface as `KubexClientException`. A missing WebSocket dependency raises `ConfigurationError`.

```python
from kubex.api._exec import ExecError
from kubex.core.exceptions import KubexClientException

try:
    result = await api.exec.run(pod_name, command=["false"])
    result.raise_for_status()
except ExecError as e:
    print(f"command failed (exit code {e.exit_code}): {e}")
except KubexClientException as e:
    print(f"WebSocket error: {e}")
```
