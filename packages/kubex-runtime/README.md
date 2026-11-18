# kubex-runtime

A controller runtime for [Kubex](https://github.com/codemageddon/kubex), modelled on
[kube-runtime](https://docs.rs/kube-runtime) from kube.rs. Runs on asyncio and trio.

- `watcher()` gets the current objects of a kind (as a streaming list, or with paged
  lists on a server without one) and watches their changes as a stream of events,
  fetching the objects again when the resource version expires and retrying
  failures with a backoff. `InitDone` and `Bookmark` events say how far the
  watch has got.
- `reflector()` keeps a `Store` up to date from a watcher; its `Writer` can be
  subscribed to, so several controllers share one watch. A store records the writes
  made for an object, and a controller holds that object until its stores have seen
  them.
- `Controller` calls a reconcile function for every object that changed, or whose
  owned or watched objects changed, and requeues it as the function asks.
- `finalizer()` runs cleanup before an object is deleted.

Documentation: https://kubex.codemageddon.me/ (the Runtime section).

```python
from kubex_runtime import Action, Controller

async def reconcile(cm: ConfigMap, ctx: Context) -> Action:
    ...
    return Action.requeue(300)

def error_policy(cm: ConfigMap, error: Exception, ctx: Context) -> Action:
    return Action.requeue(5)

await Controller(ConfigMap, Api(ConfigMap, client=client)).run(
    reconcile, error_policy, ctx
)
```

## Several controllers in one process

An operator for dependent kinds, say Deployment → ReplicaSet → Pod, runs a controller
per kind and triggers each owner from its children. When the reconcile functions read
the children from a store rather than from the API, share one reflector per kind:

```python
import anyio
from kubex_runtime import Controller, shared_reflector

async with (
    shared_reflector(rs_api) as replica_sets,
    shared_reflector(pod_api) as pods,
):
    async def reconcile_deployment(deployment: Deployment, ctx: Context) -> Action:
        ...  # finds its ReplicaSets in replica_sets.store

    deployments = Controller(Deployment, deployment_api).owns_shared(replica_sets)
    rs_controller = Controller.for_shared(ReplicaSet, replica_sets).owns_shared(pods)
    async with anyio.create_task_group() as tg:
        tg.start_soon(deployments.run, reconcile_deployment, error_policy, ctx)
        tg.start_soon(rs_controller.run, reconcile_replica_set, error_policy, ctx)
```

`shared_reflector()` runs one watch while the block runs; a watcher that gives up ends
the block with its error. To run it in a task group you already have, use
`SharedReflector(api)` and `tg.start_soon(shared.run)`. It outlives the controllers
built on it: after a lost leader election, build new controllers on it and keep its
store.

`Controller.for_shared`, `owns_shared` and `watches_shared`:

- subscribe when the controller starts and unsubscribe when it stops, so a controller
  that is built but never run never holds up the watch;
- hold every reconcile until the reflector's store is ready: reconciled before the
  ReplicaSets have listed, a Deployment would find none and create them again;
- buffer with `MergedBuffer()` by default, which keeps the latest state of each changed
  object and never makes the writer wait, so a busy controller does not hold up the
  others (the controller reads the store anyway); a child deleted and re-created under
  its name is two objects there, so its old owner still sees the deletion;
- take `adapt=` to filter what triggers a reconcile, e.g.
  `adapt=lambda s: predicate_filter(s, generation)` on `for_shared` to skip
  status-only changes. That skips every other change that leaves the generation alone
  too: a controller with a `finalizer()` would not see the finalizer it added, so
  include the finalizers in the value, and keep `None`, which always passes, for kinds
  without a generation
  (`lambda obj: None if (g := generation(obj)) is None else (g, tuple(obj.metadata.finalizers or ()))`).
  Do not
  filter `owns_shared` or `watches_shared` on the generation: a deleted child comes with
  its last state, which the filter has already seen, so it would not trigger its owner.

Compared with `owns(ReplicaSet, rs_api)`, which runs a watch of its own:

- each kind is watched once;
- an owner's trigger comes from the store its reconcile function reads, so the
  reconcile sees the change that triggered it.

Plain `owns()` and `watches()` suit reconcile functions that read related objects
from the API.

Things to get right:

- **Wait for every store you read.** `owns_shared` and `watches_shared` wait for theirs;
  `waits_for(store)` adds any other, such as a cache the reconcile function reads but
  is not triggered from. A controller that waits more than 60 s logs a warning with how
  many of its stores are still not ready.
- **Record the writes the next reconcile must see.** Reconciled again before the watch
  delivers a ReplicaSet it just created, a Deployment does not find it in the store and
  creates another. Where a child can have a fixed name, give it one, so a second create
  fails with 409 Conflict (or create it with server-side apply). Otherwise, as for a
  child with a generated name, record the write in the store the child belongs to:

  ```python
  created = await rs_api.create(replica_set)
  replica_sets.wrote(created, owner=deployment)
  ```

  The controller then holds the Deployment until every store it reads (its own, and
  those of `owns_shared`, `watches_shared` and `waits_for`) has seen the write, so no
  reconcile after it, requeued, failed or triggered by anything else, reads the store
  from before it. Record a write to the reconciled object itself the same way, in the
  controller's store. A held object takes no place under `concurrency` and stays held
  until the store catches up, which during a watch outage is when the watch recovers;
  a hold that lasts 60 s is logged. A write the watch never delivers (outside its
  namespace or selectors) is seen once a later event or bookmark passes it, so keep
  `WatcherConfig(bookmarks=True)`, the default. Writes of kinds whose
  resourceVersions are not integers (some aggregated APIs) are not waited for.

  Children in other clusters work the same way: record the write in the store of the
  reflector that watches the cluster it went to. resourceVersions are compared only
  within one store, so a write recorded in another cluster's store releases its owner
  too early or holds it far too long, and nothing can tell. The stores are fixed when
  the controller starts: for a cluster added later, rebuild the controller, or have the
  reconcile function `await store.wait_for_writes(owner)` under a timeout that raises,
  before it reads. A store that will never see its writes, such as the cache of a
  cluster that is gone for good, holds their owners until `forget_writes()` drops them.
  Call it too when a store's watch moves to another cluster (a new client), once the
  old watch has stopped: it drops the store's resourceVersion as well, which the new
  cluster's do not compare with. A re-list below the store's version (a cluster rebuilt
  or restored from an etcd snapshot) drops the writes by itself.
- **`ControllerConfig(concurrency=)` is per controller**: the caps of several
  controllers add up. Controllers on one client also share its connection pool
  (`ClientOptions(pool_size=)`).
- **Close the subscriptions you make yourself.** `SharedReflector.subscribe()` is
  bounded (1024 objects) by default, like `Writer.subscribe()`: once an unread one is
  full it holds up the watch, and every controller sharing it. Pass `MergedBuffer()`
  for a consumer that may fall behind.

`for_shared_stream`, `owns_shared_stream` and `watches_shared_stream` take any stream
of objects instead, e.g. a `Writer.subscribe()` of a `reflector()` you run yourself.
Then the rest is yours too: drain the reflector in a task of its own (not one that
reads a subscription of it), subscribe only for controllers you start, and call
`waits_for` for the stores you read.

## Threads and free-threaded Python

kubex-runtime runs on free-threaded Python (3.14t and later) and is tested there. A watch runs in
the event loop its `Api`'s client was made in, and a controller in the loop that runs it; what they
share can be used from other threads:

- a `Store` can be read and `wrote()` called from any thread, e.g. from `anyio.to_thread.run_sync()`
  in a reconcile function, and `wait_until_ready()` or `wait_for_writes()` awaited in any thread's
  event loop;
- `subscribe()` (of a `Writer` or a `SharedReflector`) works from any thread, and a subscription
  can be read in another thread's event loop than the writer's, asyncio or trio, and closed from
  any thread;
- so a `SharedReflector` running in one thread can feed controllers running in others, through
  `for_shared`, `owns_shared` and `watches_shared`.

The rest stays in one event loop: a writer is fed by one task, and a controller's results and the
stream adapters (`predicate_filter()` and the like) are read in the loop that runs them.

On free-threaded 3.14 a thread started from a task inherits its context, where anyio believes that
task's loop is running: start the thread's own loop in an empty context,
`contextvars.Context().run(anyio.run, main)`.

### Reconciling in other threads

A controller runs its reconcile function as a task in its own event loop; the function can hand
its work to other threads. With the GIL, threads help only with blocking calls: a CPU-bound
reconcile runs in parallel only on a free-threaded build.

Blocking or CPU-bound code goes to `anyio.to_thread.run_sync()`:

```python
limiter = anyio.CapacityLimiter(8)

async def reconcile(cm: ConfigMap, ctx: Context) -> Action:
    desired = await anyio.to_thread.run_sync(render, cm, ctx, limiter=limiter)
    ...  # apply `desired` through the API, here in the controller's loop
    return Action.await_change()

controller.with_config(ControllerConfig(concurrency=8))
```

- **Call the API from the reconcile function**, before or after the thread: a client works only
  in the loop it was made in. The thread can call into that loop with `anyio.from_thread.run()`.
- **Give `concurrency` the limiter's size**, so a reconcile waiting for a thread waits in the
  controller's queue and reads the object once a thread is free, not before its wait. Without a
  limiter, the reconciles share anyio's default, 40 threads, with everything else in the loop.
- **A thread cannot be cancelled**: leaving `running()` waits for the threads in flight, or, with
  `abandon_on_cancel=True`, leaves them running, writing after the controller has stopped.

An async reconcile function can run in worker threads, each running an event loop of its own,
asyncio or trio, with a client of its own: the reconcile function sends the object to a worker
and awaits the outcome. kubex-runtime has no such pool; `WorkerPool` below is one you write.

```python
async def reconcile_in_worker(client: BaseClient, cm: ConfigMap, ctx: Context) -> Action:
    api = Api(ConfigMap, client=client, namespace=cm.metadata.namespace)  # the worker's client
    ...

configuration = await configure_from_kubeconfig()
async with (
    await create_client(configuration) as client,
    WorkerPool(configuration, workers=4) as pool,
):
    async def reconcile(cm: ConfigMap, ctx: Context) -> Action:
        return await pool.run(reconcile_in_worker, cm, ctx)

    await Controller(ConfigMap, Api(ConfigMap, client=client)).run(reconcile, error_policy, ctx)
```

The controller still decides what runs and when: one reconcile of an object at a time, requeues,
`concurrency`; the error a worker raises reaches `error_policy`. What the pool has to get right:

- **Make each worker's client in its own loop**, started in an empty context (above), from one
  `ClientConfiguration`: a configuration serves clients in several threads, a client only the loop
  it was made in. Each worker has a connection pool of its own (`ClientOptions(pool_size=)`).
  Credentials that refresh are the exception: with an exec plugin or OIDC in the kubeconfig, the
  token's refresh lock belongs to the loop that loaded the configuration, so load one in each
  worker's loop instead.
- **Never wait for the other loop.** Hand a job to a worker, and its outcome back, as a callback
  the other loop runs when it gets to it: `loop.call_soon_threadsafe()` on asyncio,
  `trio.lowlevel.current_trio_token().run_sync_soon()` on trio, both taken in that loop. The
  callback puts the job on the worker's memory stream, or sets an `anyio.Event` the reconcile
  awaits. `anyio.from_thread` and `BlockingPortal` (its `start_task_soon()` too) block the calling
  thread until the other loop has run the call: two loops doing that to each other deadlock.
- **Cancel the job with its reconcile.** Leaving `running()` cancels the reconciles in flight:
  cancel the job's scope in the worker (a callback again) and wait for the job to end, shielded,
  or it writes after the controller has stopped.
- **Stop the workers after the controller**: enter the pool outside it. Close a worker's stream
  under the lock its submissions take, so a job accepted before the close is still run, and wait
  for the jobs in flight before closing the worker's client.

What crosses threads must be safe there: the context, and the objects the store hands out, which
are shared: copy one (`model_copy(deep=True)`) before changing it. A `Store` can be read, and
`wrote()` called, in a worker.

This package is alpha: its API may change in any release.
