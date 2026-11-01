# Threads & Free-threaded Python

`kubex-runtime` runs on free-threaded Python (3.14t and later) and is tested there. A watch runs in the event loop where its `Api`'s client was created, and a controller runs in the event loop that runs it. The parts they share can be used from other threads.

## What works across threads

- A `Store` can be read, and `wrote()` called, from any thread, for example from `anyio.to_thread.run_sync()` inside a reconcile function. `wait_until_ready()` and `wait_for_writes()` can be awaited in any thread's event loop.
- `subscribe()`, on a `Writer` or a `SharedReflector`, works from any thread. A subscription can be read in a different thread's event loop from the writer's, asyncio or trio, and closed from any thread.
- So a `SharedReflector` running in one thread can feed controllers running in other threads, through `for_shared()`, `owns_shared()` and `watches_shared()`.

Everything else stays in one event loop. A writer is fed by a single task, and a controller's results and the stream adapters (`predicate_filter()` and the like) are read in the loop that runs them.

!!! note "Start a thread's event loop in an empty context"
    On free-threaded 3.14, a thread started from a task inherits that task's context, in which anyio believes the task's event loop is running. Start the thread's own loop in an empty context: `contextvars.Context().run(anyio.run, main)`.

## Reconciling in other threads

A controller runs its reconcile function as a task in its own event loop, and that function can hand its work to other threads. With the GIL, threads help only with blocking calls; CPU-bound reconciles run in parallel only on a free-threaded build.

### Blocking or CPU-bound work

Send blocking or CPU-bound code to `anyio.to_thread.run_sync()`:

```python
import anyio

limiter = anyio.CapacityLimiter(8)


async def reconcile(cm: ConfigMap, ctx: Context) -> Action:
    desired = await anyio.to_thread.run_sync(render, cm, ctx, limiter=limiter)
    ...  # apply `desired` through the API, here in the controller's loop
    return Action.await_change()


controller.with_config(ControllerConfig(concurrency=8))
```

- **Call the API from the reconcile function**, before or after the thread: a client works only in the event loop it was created in. The thread can call into that loop with `anyio.from_thread.run()`.
- **Set `concurrency` to the limiter's size.** A reconcile waiting for a thread then waits in the controller's queue, and reads the object once a thread is free, not before its wait. Without a limiter, the reconciles share anyio's default limiter of 40 threads with everything else in the loop.
- **A thread cannot be cancelled.** Leaving `running()` waits for the threads in flight, or, with `abandon_on_cancel=True`, leaves them running, so they may write after the controller has stopped.

### Async reconciles in worker event loops

An async reconcile function can also run in worker threads, each running an event loop of its own (asyncio or trio) with a client of its own. The controller's reconcile function sends the object to a worker and awaits the outcome. `kubex-runtime` has no such pool; `WorkerPool` below is one you write yourself.

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

    controller = Controller(ConfigMap, Api(ConfigMap, client=client, namespace=None))
    await controller.run(reconcile, error_policy, ctx)
```

The controller still decides what runs and when: one reconcile of an object at a time, requeues, and `concurrency`. An error a worker raises reaches `error_policy`. What the pool has to get right:

- **Create each worker's client in the worker's own loop**, started in an empty context (see above), from one shared `ClientConfiguration`. A configuration can serve clients in several threads; a client serves only the loop it was created in. Each worker has a connection pool of its own (`ClientOptions(pool_size=...)`). Credentials that refresh are the exception: with an exec plugin or OIDC in the kubeconfig, the token's refresh lock belongs to the loop that loaded the configuration, so load a configuration in each worker's loop instead.
- **Never block waiting for the other loop.** Hand a job to a worker, and its outcome back, as a callback that the other loop runs when it gets to it: `loop.call_soon_threadsafe()` on asyncio, `trio.lowlevel.current_trio_token().run_sync_soon()` on trio, each taken in that loop. The callback puts the job on the worker's memory stream, or sets an `anyio.Event` the reconcile awaits. `anyio.from_thread` and `BlockingPortal` (including its `start_task_soon()`) block the calling thread until the other loop has run the call, so two loops doing that to each other deadlock.
- **Cancel the job with its reconcile.** Leaving `running()` cancels the reconciles in flight. Cancel the job's scope in the worker (with a callback again) and wait, shielded, for the job to end, or it writes after the controller has stopped.
- **Stop the workers after the controller**: enter the pool outside the controller. Close a worker's stream under the lock its submissions take, so that a job accepted before the close is still run, and wait for the jobs in flight before closing the worker's client.

Whatever crosses threads must be safe to share: the context, and the objects the store hands out. Those objects are shared, so copy one (`model_copy(deep=True)`) before changing it. A `Store` can be read, and `wrote()` called, inside a worker.
