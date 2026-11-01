# Watcher

`watcher()` turns the objects of one kind into one stream of events that does not end: first the objects that exist, then their changes. By default a single `Api.watch()` delivers both, as a [streaming list](#initial-list-strategies); on a server that does not support one, it merges `Api.list()` and `Api.watch()` instead. It does everything a hand-written watch loop has to do (see [Resuming after `Gone`](../operations/watch.md#resuming-after-gone)): it fetches the current objects, watches from the resourceVersion they are current at, reopens the watch after the server's timeout, fetches the objects again after 410 Gone, and retries failures with a backoff.

## Basic usage

```python
from kubex.api import Api
from kubex.k8s.v1_35.core.v1.pod import Pod
from kubex_runtime import Apply, Delete, InitApply, InitDone, watcher

api: Api[Pod] = Api(Pod, client=client, namespace="default")

async for event in watcher(api):
    match event:
        case InitApply(pod) | Apply(pod):
            print("present:", pod.metadata.name)
        case Delete(pod):
            print("deleted:", pod.metadata.name)
        case InitDone():
            print("initial list complete")
```

The watcher covers the `Api`'s namespace. Use `namespace=None` on the `Api` to watch every namespace.

## Events

| Event | Meaning |
|---|---|
| `Init()` | An initial sync (or a re-sync) starts. The objects that follow replace every object known so far |
| `InitApply(obj)` | An object that exists as of the current sync |
| `InitDone(resource_version)` | The sync is complete: every current object has been sent. `resource_version` is the version the objects are current at |
| `Apply(obj)` | An object was added or modified |
| `Delete(obj)` | An object was deleted. `obj` is its last state |
| `Bookmark(resource_version)` | The watch has sent every change up to `resource_version` |

The stream starts with `Init`, one `InitApply` per object and `InitDone`. Then come the changes: `Apply`, `Delete` and `Bookmark`. Bookmarks appear only after `InitDone`, and only when `bookmarks=True`, which is the default.

The [initial list strategy](#initial-list-strategies) decides where the objects between `Init` and `InitDone` come from. With a streaming list (the default) they are the initial events of the watch itself, and `InitDone` carries the resourceVersion of the bookmark that ends them. With `LIST_WATCH` they come from paged list requests, and `InitDone` carries the list's resourceVersion. The events are the same either way.

When the resourceVersion the watcher resumes from has expired (410 Gone), it syncs again with the same strategy: `Init`, the objects, and `InitDone` again. An object deleted while the watch was down produces no `Delete`; it is simply missing from the new sync. If you keep state from the events, replace that state at each `InitDone`, as a [reflector](reflector.md) does.

The events are frozen dataclasses, so you can `match` on them with positional patterns. `Event[K]` is their union.

!!! note "`Apply` versus `FinalizerApply`"
    `kubex_runtime.Apply` is the watcher event. The [finalizer](finalizer.md) events are exported as `FinalizerApply` and `FinalizerCleanup`.

## Configuration

Pass a `WatcherConfig` to choose what to watch and how:

```python
from kubex_runtime import WatcherConfig, watcher

config = WatcherConfig(label_selector="app=nginx", page_size=100)
async for event in watcher(api, config):
    ...
```

| Field | Default | Meaning |
|---|---|---|
| `label_selector` | `None` | Label selector for the list and the watch |
| `field_selector` | `None` | Field selector for the list and the watch |
| `timeout` | `290` | Server-side timeout of one watch request, in seconds. The server ends the watch after it, and the watcher reopens it from where it got to |
| `page_size` | `500` | Objects per list page (`limit`), when the watcher lists. `None` lists everything in one request |
| `bookmarks` | `True` | Ask the server for bookmarks. They keep the resume point fresh while nothing changes, and stores use them to tell which writes they have seen. A streaming list needs them |
| `request_timeout` | `...` | HTTP timeout of the list requests. `...` keeps the client's default (see [Timeouts](../operations/timeouts.md)) |
| `watch_request_timeout` | `...` | HTTP timeout of the watch requests |
| `initial_list_strategy` | `None` | How the current objects are fetched: `None` is `STREAMING_LIST_WITH_FALLBACK`, or `LIST_WATCH` with `bookmarks=False` (see [below](#initial-list-strategies)) |

### Stalled connections

A watch that has not ended 30 seconds after its `timeout` is treated as a dead connection, one that will never deliver another event. It fails with `KubexTimeoutError`, which goes to `on_error`, and the watch is reopened after the backoff. The deadline is set when the watch opens, and events do not move it. With `timeout=None` there is no deadline, and the server applies its own timeout.

## Initial list strategies

`initial_list_strategy` chooses how the watcher gets the current objects, both at the start and on every re-list:

| `InitialListStrategy` | What it does |
|---|---|
| `LIST_WATCH` | Paged list requests (`page_size` objects each), then a watch from the list's resourceVersion |
| `STREAMING_LIST` | One watch with `sendInitialEvents=true`. The server sends the current objects, then a bookmark that marks their end, then the changes, all on the same stream. This is lighter on the API server than paging through a large list. It needs the API server's `WatchList` feature: a server without it rejects the watch with 422 Unprocessable Entity, and the watcher retries it after the backoff like any other failure |
| `STREAMING_LIST_WITH_FALLBACK` (default) | `STREAMING_LIST`, but the watcher switches to `LIST_WATCH` for the rest of its life when the server rejects the streaming list with 422, or ends the stream before the bookmark that ends the initial events, as a server that ignores `sendInitialEvents` does |

The API server's `WatchList` feature is on by default in Kubernetes 1.32 and from 1.34 on; it is off by default in 1.33 and in earlier versions. On a server without it, the default costs each watcher one rejected request, logged at INFO, before it switches to paged lists. A server that ignores `sendInitialEvents` gives itself away only when it ends the watch, after `timeout`, so the store is not ready until then; that fallback is logged as a warning.

The stream looks the same with every strategy. A streaming list ends with a bookmark, so it needs `bookmarks=True`: with `bookmarks=False` the default is `LIST_WATCH`, and asking for a streaming strategy raises `ValueError`.

To keep to paged lists:

```python
from kubex_runtime import InitialListStrategy, WatcherConfig

config = WatcherConfig(initial_list_strategy=InitialListStrategy.LIST_WATCH)
```

## Errors and backoff

The watcher does not end on a failure:

- **410 Gone while watching** is routine: the watcher re-lists right away, without a backoff, and does not call `on_error`.
- **A streaming list the server does not support** makes `STREAMING_LIST_WITH_FALLBACK` (the default) switch to paged lists right away, without a backoff, and does not call `on_error` either.
- **Any other failure** is reported to `on_error(exception)` and retried after `backoff.next()` seconds. This covers a failed list page, a watch that fails to open or breaks mid-stream, and a stalled watch. A failure while listing starts the list over from its first page, and a 410 for an expired continue token counts as such a failure. A failure while watching reopens the watch from the last resourceVersion seen.
- **The stream raises** only when the backoff gives up (`next()` returns `None`), after calling `on_error` with that last exception. The default backoff never gives up.
- **`on_recovered()`** is called on the first success after a failure. A success is a whole list (a single page is not enough), a watch that delivers an event, or a watch that ends on its server timeout. Every success resets the backoff, and so does the start of the stream.

Every retried failure is also logged as a warning on the `kubex_runtime.watcher` logger.

```python
import logging

from kubex_runtime import ExponentialBackoff, watcher

logger = logging.getLogger("my-operator")

events = watcher(
    api,
    backoff=ExponentialBackoff(max_retries=10),
    on_error=lambda error: logger.warning("watch failed: %r", error),
    on_recovered=lambda: logger.info("watch recovered"),
)
```

### `ExponentialBackoff`

The default backoff is `ExponentialBackoff()`:

| Parameter | Default | Meaning |
|---|---|---|
| `initial` | `0.8` | First delay, in seconds |
| `max_delay` | `30.0` | Upper bound of every delay |
| `factor` | `2.0` | Growth factor between attempts |
| `jitter` | `True` | Draw each delay uniformly from `[delay / 2, delay]`, so that clients failing together do not all retry at the same moment |
| `max_retries` | `None` | Give up after this many failures in a row. `None` never gives up |

Any object with `next() -> float | None` and `reset()` methods satisfies the `Backoff` protocol and can be passed instead.

## Objects that do not fit the model

The watcher lists and watches with `invalid=InvalidObjects.INCLUDE`. When the model rejects an object, the watcher logs it as an error and skips it, and the stream goes on. A skipped object never reaches a store or a controller. See [Objects that do not fit the model](../operations/watch.md#objects-that-do-not-fit-the-model) for why that happens.

## Stream adapters

Adapters turn a watcher stream into a stream of objects:

| Function | Reads | Yields |
|---|---|---|
| `applied_objects(events)` | Watcher events | The objects of `Apply` and `InitApply` |
| `touched_objects(events)` | Watcher events | The objects of `Apply`, `InitApply` and `Delete` |
| `predicate_filter(objects, predicate, *, ttl=3600.0)` | Objects | An object only if `predicate(obj)` changed since that object last came |

```python
from kubex.api import Api
from kubex.k8s.v1_35.apps.v1.deployment import Deployment
from kubex_runtime import applied_objects, generation, predicate_filter, watcher

deployments: Api[Deployment] = Api(Deployment, client=client, namespace=None)

async for deployment in predicate_filter(
    applied_objects(watcher(deployments)), generation
):
    print("spec changed:", deployment.metadata.name)
```

Each adapter closes the stream it reads when it stops, so closing the outermost one closes the watch too.

### Predicates

A predicate maps an object to a hashable value. `predicate_filter` passes an object when its value differs from the one it had the last time that object came through. An object whose value is `None` always passes. Two predicates are included:

| Predicate | Value | Passes on |
|---|---|---|
| `generation` | `(uid, metadata.generation)` | Spec changes, for kinds with a status subresource. Kinds without a generation always pass |
| `resource_version` | `metadata.resourceVersion` | Every change |

`ttl` is how long an object's value is remembered after it was last seen. A forgotten object passes the next time it comes. This keeps objects that no longer exist, such as children with generated names, from piling up. `ttl=None` keeps every value forever.

!!! warning "`generation` skips more than status changes"
    Filtering on `generation` drops every change that leaves the generation alone. That includes metadata changes, such as the finalizer that [`finalizer()`](finalizer.md) adds and then waits to see, and deletions, which arrive with the object's last state. Two consequences:

    - Do not filter the objects a controller owns or watches on `generation`: their deletions would trigger nothing.
    - For a controller with a finalizer, include the finalizers in the value, and keep `None` for kinds without a generation, so that their changes still pass:
      `lambda obj: None if (g := generation(obj)) is None else (g, tuple(obj.metadata.finalizers or ()))`.
