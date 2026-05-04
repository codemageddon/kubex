# Watch

`api.watch()` opens a long-lived HTTP stream and yields `WatchEvent` objects as the Kubernetes API server emits them. It is an async generator — use it inside an `async for` loop.

## Basic usage

```python
from kubex.api import Api
from kubex.client import create_client
from kubex.k8s.v1_35.core.v1.pod import Pod

client = await create_client()
async with client:
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    async for event in api.watch():
        print(event.type, event.object.metadata.name)
```

## `WatchEvent`

Each yielded value is a `WatchEvent[ResourceType]`:

| Attribute | Type | Description |
|---|---|---|
| `event.type` | `EventType` | `ADDED`, `MODIFIED`, `DELETED`, or `BOOKMARK` |
| `event.object` | `ResourceType | Bookmark` | Fully parsed resource (or `Bookmark` for bookmark events) |

```python
from kubex_core.models.watch_event import EventType

async for event in api.watch():
    match event.type:
        case EventType.ADDED:
            print(f"new pod: {event.object.metadata.name}")
        case EventType.DELETED:
            print(f"pod gone: {event.object.metadata.name}")
```

## Filtering

Pass `label_selector=` or `field_selector=` to narrow the stream:

```python
async for event in api.watch(label_selector="app=nginx"):
    ...
```

## Bookmarks and `allow_bookmarks`

Pass `allow_bookmarks=True` to request periodic `BOOKMARK` events from the server. Bookmark events carry an up-to-date `resourceVersion` in `event.object.metadata.resource_version` but no other data — they are checkpoints, not data.

The main reason to enable bookmarks is to keep an up-to-date `resourceVersion` even when the watched resources rarely change. Without bookmarks the saved `resourceVersion` ages with every quiet minute, and is far more likely to have been compacted (HTTP 410 `Gone`) by the time you reconnect.

```python
async for event in api.watch(allow_bookmarks=True, namespace=None):
    if event.type == EventType.BOOKMARK:
        rv = event.object.metadata.resource_version
        print(f"checkpoint: resourceVersion={rv}")
```

## Watching across all namespaces

Pass `namespace=None` to watch across every namespace, even when the `Api` was created with a default namespace:

```python
async for event in api.watch(namespace=None):
    ns = event.object.metadata.namespace
    name = event.object.metadata.name
    print(f"{event.type}: {ns}/{name}")
```

## `send_initial_events` pattern

Kubernetes 1.27+ supports `sendInitialEvents=true`, which causes the watch stream to first emit `ADDED` events for every existing resource before switching to live updates. Set `send_initial_events=True` together with `allow_bookmarks=True` to get a single stream that covers both current state and future changes:

```python
async for event in api.watch(send_initial_events=True, allow_bookmarks=True):
    if event.type == EventType.BOOKMARK:
        print("initial list complete, watching for changes now")
    else:
        print(event.type, event.object.metadata.name)
```

## Restart-on-`Gone` pattern

The Kubernetes API server expires watch streams with HTTP 410 `Gone` when the `resourceVersion` becomes too old, and closes streams on its own default `timeoutSeconds`. The simplest robust pattern is to re-call `watch()` with `send_initial_events=True` on every reconnect — the server replays a synthetic `ADDED` snapshot before resuming live updates, so you do not need a separate `list()` step:

```python
from kubex.core.exceptions import Gone

while True:
    try:
        async for event in api.watch(
            allow_bookmarks=True,
            send_initial_events=True,
        ):
            handle(event)
    except Gone:
        # resourceVersion expired — just re-watch.
        # send_initial_events=True replays the snapshot before live updates.
        continue
```

## Server-side timeout

Pass `timeout_seconds=` to set a server-side timeout on the watch call (sent as the Kubernetes `timeoutSeconds` query parameter). The server closes the stream after this many seconds; your loop can then reconnect:

```python
async for event in api.watch(timeout_seconds=60):
    ...
```

## Example from `examples/watch_pods.py`

!!! note "asyncio-only example"
    This example uses `asyncio.create_task` and `asyncio.CancelledError`, which are asyncio-specific.
    Trio users should replace these with [`anyio.create_task_group()`](https://anyio.readthedocs.io/en/stable/tasks.html) instead.

```python
import asyncio
from contextlib import suppress
from typing import cast

from kubex.api import Api
from kubex.client import create_client
from kubex.k8s.v1_35.core.v1.container import Container
from kubex.k8s.v1_35.core.v1.pod import Pod
from kubex.k8s.v1_35.core.v1.pod_spec import PodSpec
from kubex_core.models.metadata import ObjectMetadata

async def watcher(pod_api: Api[Pod]) -> None:
    async for event in pod_api.watch(allow_bookmarks=True, namespace=None):
        print(event)

async def main() -> None:
    client = await create_client()
    async with client:
        api: Api[Pod] = Api(Pod, client=client, namespace="default")
        _watcher = asyncio.create_task(watcher(api))
        pod_name: str | None = None
        try:
            _pod = await api.create(
                Pod(
                    metadata=ObjectMetadata(generate_name="example-pod-"),
                    spec=PodSpec(containers=[Container(name="example", image="nginx")]),
                ),
            )
            pod_name = cast(str, _pod.metadata.name)
        finally:
            if pod_name is not None:
                print(await api.delete(pod_name))
            _watcher.cancel()
            with suppress(asyncio.CancelledError):
                await _watcher
```
