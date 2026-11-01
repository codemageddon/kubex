# Several Controllers

An operator for dependent kinds, such as Deployment → ReplicaSet → Pod, runs one controller per kind and triggers each owner from its children. When the reconcile functions read the children from a store rather than from the API, share one [reflector](reflector.md#shared-reflectors) per kind between the controllers.

## Example

```python
import anyio

from kubex.k8s.v1_35.apps.v1.deployment import Deployment
from kubex.k8s.v1_35.apps.v1.replica_set import ReplicaSet
from kubex_runtime import Action, Controller, shared_reflector

async with (
    shared_reflector(rs_api) as replica_sets,
    shared_reflector(pod_api) as pods,
):

    async def reconcile_deployment(deployment: Deployment, ctx: Context) -> Action:
        uid = deployment.metadata.uid
        mine = replica_sets.store.find(
            lambda rs: any(o.uid == uid for o in rs.metadata.owner_references or ())
        )
        ...  # create or update ReplicaSets so that `mine` matches the Deployment
        return Action.await_change()

    deployments = Controller(Deployment, deployment_api).owns_shared(replica_sets)
    rs_controller = Controller.for_shared(ReplicaSet, replica_sets).owns_shared(pods)

    async with anyio.create_task_group() as tg:
        tg.start_soon(deployments.run, reconcile_deployment, error_policy, ctx)
        tg.start_soon(rs_controller.run, reconcile_replica_set, error_policy, ctx)
```

`shared_reflector()` runs one watch while the block runs. If its watcher gives up, the error ends the block. To run the watch in a task group you already have, create a `SharedReflector(api)` and start `shared.run` in that group.

## Shared triggers

`Controller.for_shared(model, shared)` builds a controller of the objects of a shared reflector, reading its store. `owns_shared(shared)` and `watches_shared(shared, mapper)` add triggers from one, like [`owns()` and `watches()`](controller.md#triggers). All three:

- **subscribe when the controller starts and unsubscribe when it stops**, so a controller that is built but never run never holds up the watch;
- **hold every reconcile until the reflector's store is ready.** Reconciled before the ReplicaSets have been listed, a Deployment would find none and create them again;
- **buffer with `MergedBuffer()` by default.** It keeps the latest state of each changed object and never makes the writer wait, so a busy controller does not hold up the others; the controller reads the latest state from the store anyway. A child deleted and re-created under its name counts as two objects, so its old owner still sees the deletion. Pass `buffer=` to choose another [buffer](reflector.md#buffers);
- **take `adapt=`**, a function that wraps the subscription stream, to filter what triggers a reconcile.

### Filtering triggers

`adapt=lambda stream: predicate_filter(stream, generation)` on `for_shared()` skips status-only changes. Keep in mind that it skips every other change that leaves the generation alone, too:

- A controller with a [`finalizer()`](finalizer.md) would not see the finalizer it added. Include the finalizers in the value, and keep `None` for kinds without a generation, so that their changes still pass: `lambda obj: None if (g := generation(obj)) is None else (g, tuple(obj.metadata.finalizers or ()))`.
- Do not filter `owns_shared()` or `watches_shared()` on the generation. A deleted child arrives with its last state, which the filter has already seen, so it would not trigger its owner.

### Compared with `owns()` and `watches()`

`owns(ReplicaSet, rs_api)` runs a watch of its own for each controller. With `owns_shared(replica_sets)` instead:

- each kind is watched once, however many controllers use it;
- an owner's trigger comes from the store its reconcile function reads, so the reconcile always sees the change that triggered it.

Plain `owns()` and `watches()` suit reconcile functions that read their related objects from the API.

## Wait for every store you read

`owns_shared()` and `watches_shared()` wait for their stores. `waits_for(*stores)` adds any other store the reconcile function reads, such as a cache it is not triggered from:

```python
controller = Controller.for_shared(Deployment, deployments).waits_for(services.store)
```

A controller that has waited for more than 60 s logs a warning with the number of its stores that are still not ready.

## Recording writes

A store lags behind your own writes: it sees them only when the watch delivers them. If a Deployment is reconciled again before the watch has delivered a ReplicaSet it just created, the reconcile does not find the ReplicaSet in the store and creates another one.

When a child can have a fixed name, give it one, so that a second create fails with 409 Conflict, or create it with server-side apply. Otherwise, for example for a child with a generated name, record the write in the store the child belongs to:

```python
created = await rs_api.create(replica_set)
replica_sets.wrote(created, owner=deployment)
```

The controller then holds the Deployment until every store it reads has seen the write: its own store, and those of `owns_shared()`, `watches_shared()` and `waits_for()`. No later reconcile of the Deployment, whether requeued, retried or triggered by anything else, reads a store from before the write. Record a write to the reconciled object itself the same way, in the controller's own store.

- `wrote(obj, owner=...)` takes the object the API returned from a create, update or patch, and the object being reconciled. It raises `ValueError` if `owner` has no uid. It is available on `Store` and on `SharedReflector`.
- A held object does not count against `concurrency`. It stays held until the store catches up, which during a watch outage means until the watch recovers. A hold that lasts 60 s is logged.
- A store notices a write when its watch delivers that object, or a later event or bookmark passes the write's resourceVersion. A write the watch never delivers, because it is outside the watch's namespace or selectors, is seen only once a later event or bookmark passes it, so keep `WatcherConfig(bookmarks=True)`, the default.
- Writes of kinds whose resourceVersions are not integers (some aggregated APIs) are not recorded, and the store logs a warning once.
- To wait for the writes yourself, outside a controller, `await store.wait_for_writes(owner)`.

### Children in other clusters

Children in other clusters work the same way: record the write in the store of the reflector that watches the cluster the write went to. A store compares resourceVersions only with its own cluster's, so a write recorded in another cluster's store releases its owner too early, or holds it far too long, and nothing can detect the mistake.

The stores a controller reads are fixed when it starts. For a cluster added later, rebuild the controller, or have the reconcile function `await store.wait_for_writes(owner)`, under a timeout that raises, before it reads that store.

A store that will never see its writes, such as the cache of a cluster that is gone for good, holds their owners until you call `forget_writes()`. Call it too when a store's watch moves to another cluster (a new client), once the old watch has stopped: it also drops the resourceVersion the store has reached, which does not compare with the new cluster's. A re-list below the store's resourceVersion, from a cluster that was rebuilt or restored from an etcd snapshot, drops the writes by itself.

## Concurrency and connections

`ControllerConfig(concurrency=...)` applies to one controller: the limits of several controllers add up. Controllers built on one client also share its connection pool, which `ClientOptions(pool_size=...)` sizes (see [ClientOptions](../concepts/clients.md#clientoptions)).

## Close the subscriptions you make yourself

`SharedReflector.subscribe()` is bounded (1024 objects) by default, like `Writer.subscribe()`. Once a subscription nobody reads is full, it holds up the watch, and with it every controller that shares the reflector. Pass `MergedBuffer()` for a consumer that may fall behind, and close every subscription you stop reading.

## Your own streams

`for_shared_stream(model, stream, store)`, `owns_shared_stream(stream)` and `watches_shared_stream(stream, mapper)` take any async iterable of objects instead of a shared reflector, for example a `Writer.subscribe()` of a [`reflector()`](reflector.md#running-a-reflector) you run yourself. The controller closes the stream when it stops. Everything a `SharedReflector` does for you is then your job:

- run the reflector in a task of its own, not in one that reads one of its subscriptions;
- subscribe only for controllers you actually start;
- call `waits_for()` for the stores you read. The store given to `for_shared_stream()` is the controller's own, which it always waits for.
