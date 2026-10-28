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
| `event.is_initial_events_end` | `bool` | `True` only for the bookmark that ends the initial events (see [`send_initial_events` pattern](#send_initial_events-pattern)) |

`ERROR` events are never yielded: the generator raises the matching exception instead — most importantly `Gone` (HTTP 410) when the requested `resourceVersion` is too old. See [Resuming after `Gone`](#resuming-after-gone).

```python
from kubex.core.watch_event import EventType

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

`send_initial_events=True` makes the stream start with synthetic `ADDED` events for every existing resource, then a `BOOKMARK` annotated with `k8s.io/initial-events-end: "true"`, then live updates — current state and future changes in one stream. The server requires bookmarks for this, so `allow_bookmarks` defaults to `True` when `send_initial_events=True` (passing `allow_bookmarks=False` together with it raises `ValueError`). It needs the API server's `WatchList` feature; a server without it rejects the request with `422`.

`event.is_initial_events_end` is `True` only for that bookmark. Periodic checkpoint bookmarks look the same apart from the annotation, so they return `False`:

```python
async for event in api.watch(send_initial_events=True):
    if event.is_initial_events_end:
        print("initial state complete, watching for changes now")
    elif event.type != EventType.BOOKMARK:
        print(event.type, event.object.metadata.name)
```

### Where to resume from

The initial `ADDED` events carry each object's own `resourceVersion`, in no particular order, so none of them is a point to resume from. The end bookmark's `resourceVersion` is the first one:

- If the stream ends before the end bookmark, discard what you collected and start again with `send_initial_events=True`.
- After it, resume with `watch(resource_version=...)` from the last `resourceVersion` you saw (an event's or a bookmark's), as in [Resuming after `Gone`](#resuming-after-gone).

## Resuming after `Gone`

A watch does not last forever. The server ends the stream cleanly after `timeout_seconds` (or its own default, usually 30–60 minutes), and it raises `Gone` (HTTP 410) — on connect, or as an `ERROR` event mid-stream — when the `resourceVersion` you resume from has been compacted away. A long-running watcher therefore tracks the last `resourceVersion` it saw, resumes from it after a normal end of stream, and re-lists to get a fresh one after `Gone`. Bookmarks keep that `resourceVersion` current while nothing changes, which makes `Gone` far less likely:

```python
from kubex.core.exceptions import Gone
from kubex.core.watch_event import EventType


async def watch_forever(api: Api[Pod]) -> None:
    resource_version: str | None = None
    while True:
        if resource_version is None:
            # (Re-)list: the current state plus a resourceVersion to watch from.
            pods = await api.list()
            for pod in pods.items:
                handle_existing(pod)
            resource_version = pods.metadata.resource_version
        try:
            async for event in api.watch(
                resource_version=resource_version, allow_bookmarks=True
            ):
                resource_version = (
                    event.object.metadata.resource_version or resource_version
                )
                if event.type != EventType.BOOKMARK:
                    handle(event)
        except Gone:
            # Too old to resume from: start over with a fresh list.
            resource_version = None
        # A normal end of stream (server-side timeout) resumes from
        # resource_version on the next iteration.
```

Events between the list and the watch are not lost: watching from the list's `resourceVersion` delivers everything that changed after it. Changes that happened while the watcher was disconnected for longer than the server keeps history are covered by the re-list, so `handle_existing` should reconcile (update or create local state, and drop objects that no longer exist) rather than assume a clean slate.

## Objects that do not fit the model

By default, an object the model cannot parse raises pydantic's `ValidationError`, which ends the stream. This mostly happens with custom resources: the API server does not re-validate objects stored before a CRD schema change, so an old object can break a model written for the current schema. Reconnecting does not help, because the same object comes back.

Pass `invalid=InvalidObjects.INCLUDE` (or the string `"include"`) to keep going. Such an object then arrives as an `InvalidWatchEvent` instead of a `WatchEvent`:

| Attribute | Type | Description |
|---|---|---|
| `event.type` | `EventType` | `ADDED`, `MODIFIED` or `DELETED` |
| `event.object.raw` | `dict[str, Any]` | The object as the server sent it |
| `event.object.error` | `ValidationError` | Why it does not fit the model |
| `event.object.metadata` | `ObjectMetadata` | Its metadata; always has a `name` |

```python
from kubex.core.params import InvalidObjects
from kubex.core.watch_event import InvalidWatchEvent

async for event in api.watch(invalid=InvalidObjects.INCLUDE):
    if isinstance(event, InvalidWatchEvent):
        print(f"skipping {event.object.metadata.name}: {event.object.error}")
        continue
    handle(event)
```

Both kinds of event have `type` and `object.metadata`, so code that only needs an object's name, namespace or `resourceVersion` (keeping a resume point, or dropping a deleted object from a cache) works on both without the `isinstance` check.

Only `ADDED`, `MODIFIED` and `DELETED` objects are tolerated. These still raise, because they mean the stream itself is broken: an `ERROR` event, a bookmark that does not parse, an object without a readable `metadata.name`, and a line that is not JSON.

`list()` takes the same option; see [Objects that do not fit the model](crud.md#objects-that-do-not-fit-the-model) for lists. Other calls still parse the object with the model: `get()` raises `ValidationError` for it, and so do `delete()`, `patch()` and `replace()`, after the server has carried out the change. Use [`api.metadata`](../subresources/metadata.md), which only parses metadata (for example, to remove a finalizer), or a looser model for those.

## Server-side timeout

Pass `timeout_seconds=` to set a server-side timeout on the watch call (sent as the Kubernetes `timeoutSeconds` query parameter). The server closes the stream cleanly after this many seconds and the `async for` loop simply ends; reconnect as shown above:

```python
async for event in api.watch(timeout_seconds=60):
    ...
```

## Client-side timeouts

A watch can stay quiet for minutes, so it does not inherit the client's short request timeouts: when `request_timeout` is left unset, a watch stream only applies the connect timeout and otherwise waits for the server to send events or end the stream (bound it with `timeout_seconds` instead). Passing an explicit `request_timeout` applies it as given — a short read or total timeout will cut off a quiet stream with a timeout error, so only do that deliberately (or pass `request_timeout=None` to disable client-side timeouts entirely).

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
