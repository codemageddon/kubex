# Controller

A `Controller` calls a reconcile function for the objects of one kind: when an object changes, when the objects it owns or watches change, and when an earlier reconcile asked to run again. The reconcile function compares the object's desired state with the actual state of the world, and changes the world to match.

## Building and running

```python
from kubex.api import Api
from kubex.k8s.v1_35.apps.v1.deployment import Deployment
from kubex_runtime import Controller, ControllerConfig, WatcherConfig

deployments: Api[Deployment] = Api(Deployment, client=client, namespace=None)

config = WatcherConfig(label_selector="app.kubernetes.io/managed-by=my-operator")
controller = Controller(Deployment, deployments, config).with_config(
    ControllerConfig(concurrency=8)
)

await controller.run(reconcile, error_policy, ctx)
```

`Controller(model, api, watcher_config=None, *, buffer=None)` runs its own watch of `api` into a store, available as `controller.store`. `buffer` is how that watch buffers changes for the controller (see [Buffers](reflector.md#buffers)); the default is `BoundedBuffer()`.

The builder methods (`with_config()`, `owns()`, `watches()`, …) return the controller, so you can chain them.

## The reconcile function

```python
from kubex_runtime import Action


async def reconcile(deployment: Deployment, ctx: Context) -> Action:
    ...  # make the world match `deployment`
    return Action.requeue(300)


def error_policy(deployment: Deployment, error: Exception, ctx: Context) -> Action:
    return Action.requeue(10)
```

- `reconcile(obj, ctx)` is an async function. `obj` is the object's latest state from the controller's store, and `ctx` is the `context` you passed to `run()`, shared by every reconcile.
- It returns an `Action`. `Action.requeue(seconds)` reconciles the object again after that delay, unless a change comes first. `Action.await_change()` waits for the next trigger.
- `error_policy(obj, error, ctx)` is a plain function. It is called with the exception a reconcile raised, and the `Action` it returns schedules the retry. If the error policy itself raises, the error is logged and the object waits for its next trigger.

A reconcile function gets the current state of the object, not the change that triggered it, and it may be called any number of times, for any reason. Write it to be idempotent: it should do nothing when the world already matches.

A deleted object is not reconciled, since it is no longer in the store. To act on a deletion, use a [finalizer](finalizer.md).

## Triggers

A controller reconciles the objects of its own watch, plus the triggers you add with the builder methods:

| Method | Reconciles |
|---|---|
| (own watch) | Every object of the controller's kind that is listed, added or modified |
| `owns(model, api, watcher_config=None)` | The controlling owner of every changed object of `api`: the `ownerReferences` entry with `controller: true` that is of the controller's kind |
| `watches(model, api, mapper, watcher_config=None)` | The objects `mapper(obj)` returns, as `ObjectRef`s, for every changed object of `api` |
| `reconcile_on(stream)` | Every `ObjectRef` an async iterable yields |
| `reconcile_all_on(stream)` | Every object in the controller's store, for each item an async iterable yields |
| `owns_shared()`, `watches_shared()`, … | The same, from a [shared reflector](shared-reflectors.md) |

`owns()` and `watches()` start a watch of their own for `api` when the controller runs. A deleted object triggers its owner or mapped objects too, and so does an object that a re-list no longer finds because it was deleted while the watch was down.

### Owned objects

```python
from kubex.k8s.v1_35.apps.v1.replica_set import ReplicaSet

replica_sets: Api[ReplicaSet] = Api(ReplicaSet, client=client, namespace=None)
controller = Controller(Deployment, deployments).owns(ReplicaSet, replica_sets)
```

An owner is either in the same namespace as its dependent or cluster-scoped. The controller's kind decides which: a namespaced controller looks for the owner in the dependent's namespace, a cluster-scoped one looks for it outside any namespace. For example, a `Controller(Namespace, ...)` that `owns()` ConfigMaps is triggered by every ConfigMap whose controlling owner is a Namespace.

### Watched objects

`watches()` takes a mapper, a plain function that returns the references to reconcile for a changed object. It can read the controller's store:

```python
from collections.abc import Iterator

from kubex.k8s.v1_35.core.v1.config_map import ConfigMap
from kubex_runtime import ObjectRef

controller = Controller(Deployment, deployments)


def deployments_using(cm: ConfigMap) -> Iterator[ObjectRef]:
    for deployment in controller.store.namespaced(cm.metadata.namespace):
        if uses_config_map(deployment, cm.metadata.name):
            yield ObjectRef.from_obj(deployment)


config_maps: Api[ConfigMap] = Api(ConfigMap, client=client, namespace=None)
controller.watches(ConfigMap, config_maps, deployments_using)
```

If a mapper raises, the error is logged and that change triggers nothing.

### Other triggers

`reconcile_on()` reconciles the objects an async iterable refers to, for example ones sent from another task:

```python
import anyio

send, receive = anyio.create_memory_object_stream[ObjectRef]()
controller.reconcile_on(receive)
...
await send.send(ObjectRef.of(Deployment, "web", "default"))
```

`reconcile_all_on()` reconciles every object in the store on each item of an async iterable, for example on a timer:

```python
from collections.abc import AsyncIterator


async def every(seconds: float) -> AsyncIterator[None]:
    while True:
        await anyio.sleep(seconds)
        yield None


controller.reconcile_all_on(every(600))
```

A trigger stream that ends simply stops triggering. A trigger stream that raises ends the controller with that error.

## Scheduling

- **One reconcile per object at a time.** A trigger that comes while an object is being reconciled runs right after the reconcile ends.
- **Triggers merge.** The controller keeps one pending entry per object, and the earliest wins. If a reconcile requeues an object in 300 s and the object changes 10 s later, it is reconciled at 10 s, and that reconcile's action schedules the next one.
- **A trigger for an object that is not in the store is dropped.** This is how deleted objects are skipped.
- **Nothing is reconciled before the store is ready**, nor before the stores given to [`waits_for()`](shared-reflectors.md#wait-for-every-store-you-read) are. Triggers that come earlier wait. A controller still waiting after 60 s logs a warning with the number of stores that are not ready.
- **Objects with unseen writes are held.** A controller holds an object back while one of its stores has a write recorded for it that the store has not seen yet. See [Recording writes](shared-reflectors.md#recording-writes).

`ControllerConfig` tunes the scheduling:

| Field | Default | Meaning |
|---|---|---|
| `debounce` | `0.0` | Delays every trigger, requeues included, by this many seconds. Triggers for one object that come within the delay merge, and each one restarts it, so a burst of changes is reconciled once, `debounce` seconds after the last change |
| `concurrency` | `0` | Maximum number of reconciles running at once. `0` means no limit |

```python
controller.with_config(ControllerConfig(debounce=1.0, concurrency=16))
```

## Results

`run()` reconciles until it is cancelled and logs every failed reconcile. To see each outcome yourself, use `running()`, an async context manager that reconciles while its block runs:

```python
async with controller.running(reconcile, error_policy, ctx) as results:
    async for result in results:
        if result.error is not None:
            metrics.reconcile_errors.inc()
```

Each `ReconcileResult` has:

| Attribute | Type | Meaning |
|---|---|---|
| `obj_ref` | `ObjectRef` | The object reconciled |
| `reason` | `ReconcileReason` | Why it was reconciled |
| `action` | `Action | None` | What `reconcile` (or `error_policy`) returned. `None` if the error policy raised |
| `error` | `Exception | None` | What `reconcile` raised |

`reason.name` is one of these, and `reason.related` names the owned or watched object for `"related object updated"`:

| `reason.name` | Triggered by |
|---|---|
| `"object updated"` | The object itself changed |
| `"related object updated"` | `owns()`, `watches()` and their shared variants |
| `"reconciler requested retry"` | `Action.requeue()` returned by `reconcile` |
| `"error policy requested retry"` | `Action.requeue()` returned by `error_policy` |
| `"bulk reconcile"` | `reconcile_all_on()` |
| `"unknown"` | `reconcile_on()` |

Read the results: once 128 of them are waiting unread, reconciles pause until you catch up. Leaving the block cancels the reconciles in flight.

### Running several controllers

`run()` returns only when it is cancelled, so start each controller in a task group:

```python
async with anyio.create_task_group() as tg:
    tg.start_soon(deployment_controller.run, reconcile_deployment, error_policy, ctx)
    tg.start_soon(config_map_controller.run, reconcile_config_map, error_policy, ctx)
```

When the controllers read each other's kinds, share one watch per kind between them. See [Several Controllers](shared-reflectors.md).

### A controller runs once

A controller keeps its store and the streams it was given, so it runs only once. Entering `running()` or `run()` a second time, during or after the first run and from any thread, raises `RuntimeError`. To run again, after losing a leader election for example, build a new controller.

## Failures of the watches

The watches a controller runs itself (its own watch, and those of `owns()` and `watches()`) retry every failure with the default backoff, which never gives up. To bound the backoff, or to get `on_error` and `on_recovered` callbacks, watch through a [`SharedReflector`](reflector.md#shared-reflectors) and build the controller with `Controller.for_shared()`, `owns_shared()` and `watches_shared()`.

## `ObjectRef`

`ObjectRef(group, kind, name, namespace=None)` names one object of one kind. It is the key of stores and controllers, and what mappers and `reconcile_on()` streams return:

| Constructor | Refers to |
|---|---|
| `ObjectRef.of(Model, name, namespace=None)` | The object `name` of the kind `Model` |
| `ObjectRef.from_obj(obj)` | `obj`, which must have a name |
| `ObjectRef.from_owner(owner_reference, namespace=None)` | The owner an `OwnerReference` names. Pass the dependent's namespace for a namespaced owner kind, `None` for a cluster-scoped one |

Two references are equal when they name the same object of the same kind. The core group can be given as `""` or `"core"`; it is stored as `"core"`. `str(ref)` reads like `ConfigMap.core default/settings`.

## Logging

The runtime logs through the standard `logging` module, on the `kubex_runtime.watcher`, `kubex_runtime.reflector` and `kubex_runtime.controller` loggers. `run()` logs every failed reconcile at `ERROR`, with its traceback. Every reconcile is logged at `DEBUG`.
