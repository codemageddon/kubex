# Reflectors & Stores

A reflector keeps an in-memory cache of one kind of object up to date from a [watcher](watcher.md). The cache has two sides: a `Writer`, which applies the watcher's events, and a `Store`, which reads the result. Controllers read the objects they reconcile from a store, and so can your reconcile functions, instead of calling the API server.

## Running a reflector

```python
import anyio

from kubex.api import Api
from kubex.k8s.v1_35.core.v1.pod import Pod
from kubex_runtime import Writer, reflector, watcher

api: Api[Pod] = Api(Pod, client=client, namespace=None)
writer: Writer[Pod] = Writer()
pods = writer.as_reader()


async def keep_pods() -> None:
    async for event in reflector(writer, watcher(api)):
        pass  # the store already has the change; react to `event` here if you like


async with anyio.create_task_group() as tg:
    tg.start_soon(keep_pods)
    await pods.wait_until_ready()
    print(len(pods), "pods")
```

`reflector(writer, stream)` applies each event to the writer, then passes the event on. The store fills only while something iterates the reflector, so run it in a task of its own.

`store()` returns a new `(Store, Writer)` pair. Its type parameter can only be inferred from an annotation, so an annotated `Writer()` and its `as_reader()`, as above, is often simpler.

For a cache that several consumers share, [`SharedReflector`](#shared-reflectors) wraps the watcher, the writer and the store together.

## Reading a store

| Method | Returns |
|---|---|
| `store.get(ref)` | The object an [`ObjectRef`](controller.md#objectref) refers to, or `None`. A reference to another kind finds nothing, even when the namespace and name match |
| `store.get_named(namespace, name)` | The object `namespace/name`, or `None`. Use `None` as the namespace for cluster-scoped objects |
| `store.state()` | Every object |
| `store.namespaced(namespace)` | Every object in `namespace` |
| `store.find(predicate)` | Every object for which `predicate(obj)` is true |
| `len(store)`, `ref in store` | The number of objects, and whether the store has the object `ref` |
| `store.is_ready()`, `await store.wait_until_ready()` | Whether the first list has been applied, and a way to wait until it has |

A store is empty and not ready until the first `InitDone`. Once ready it stays ready, through every re-list.

A re-list is applied all at once. The objects from `Init` to `InitDone` are collected separately and swapped in at `InitDone`, so a reader never sees a half-listed store. Until then the store keeps its previous contents.

!!! warning "Objects in a store are shared"
    A store hands out the cached objects themselves, shared with every other reader. Treat them as read-only, and copy one (`obj.model_copy(deep=True)`) before changing it, for example to send it back with `api.replace()`.

## Subscribing to changes

`writer.subscribe()` returns a subscription: an async iterator of every object the writer applied, delivered after the writer applied it. When a subscriber gets an object, the store already has it, or, for a deletion, no longer has it.

```python
from kubex_runtime import MergedBuffer

async with writer.subscribe(MergedBuffer()) as changes:
    async for pod in changes:
        print("changed:", pod.metadata.name)
```

A subscription delivers:

- every added or modified object;
- every deleted object, with its last state;
- on a re-list, every object the list found, and the last state of every object it no longer found, including one that has been re-created under the same name with another uid.

A subscription made after the store is ready starts with every object in the store, so a late subscriber misses nothing.

### Buffers

The `buffer` argument chooses what happens when a subscriber reads slower than the writer writes:

| Buffer | Behaviour |
|---|---|
| `BoundedBuffer(size=1024)` (default) | Every change, in order, through a queue of at most `size` objects. When the queue is full, the writer waits for the subscriber, so a subscriber that falls behind holds up the watch and the store for every other reader |
| `MergedBuffer()` | The latest state of each changed object, one entry per object. A change to an object that is already waiting replaces it in place, so the subscriber skips the states in between and the writer never waits. An object deleted and re-created under its name counts as two objects (their uids differ), so the deletion still comes. The buffer holds at most the objects in the store plus those deleted since the subscriber last read. It suits consumers that read the latest state anyway, as controllers do |

!!! warning "Close what you subscribe"
    Close a subscription you stop reading, with `async with`, `close()` or `aclose()`. The writer keeps sending to an open subscription, and a full `BoundedBuffer` that nobody reads holds up the writer.

    For the same reason, do not iterate the reflector in the task that reads one of its bounded subscriptions. Once the subscription is full, that task would wait on itself.

## Shared reflectors

`SharedReflector` bundles a watcher, a writer and its store for several consumers: [controllers](shared-reflectors.md) and your own subscribers. `shared_reflector()` runs its watch while an `async with` block runs:

```python
from kubex_runtime import MergedBuffer, shared_reflector

async with shared_reflector(api) as pods:
    await pods.store.wait_until_ready()
    async with pods.subscribe(MergedBuffer()) as changes:
        async for pod in changes:
            ...
```

`SharedReflector(api, config=None, *, backoff=None, on_error=None, on_recovered=None)` and `shared_reflector()` take the same arguments as [`watcher()`](watcher.md#errors-and-backoff).

| Member | What it does |
|---|---|
| `shared.store` | Its `Store` |
| `shared.subscribe(buffer=None)` | A subscription, as `Writer.subscribe()` (`BoundedBuffer()` by default) |
| `shared.wrote(obj, owner=...)`, `shared.forget_writes()` | Record writes in the store, or drop them. See [Recording writes](shared-reflectors.md#recording-writes) |
| `await shared.run()` | Runs the watch until cancelled. Raises the watcher's error if its backoff gives up |

`shared_reflector()` runs `run()` in a task group of its own. If the watcher gives up, its error ends the block and cancels what the block runs. Leaving the block stops the watch. To run the watch in a task group you already have, create a `SharedReflector(api)` and start `shared.run` in that group.

Only one `run()` can be active at a time: starting another while one runs, in any thread, raises `RuntimeError`. Run again after it ended, it lists anew and keeps its store and subscriptions, and its backoff starts over. A shared reflector outlives the controllers built on it: after a lost leader election, for example, you can build new controllers on the same reflector and keep its store.
