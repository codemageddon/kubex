# Finalizers

A [finalizer](https://kubernetes.io/docs/concepts/overview/working-with-objects/finalizers/) stops the API server from deleting an object until a controller has cleaned up after it: removed an external resource, released a lease, and so on. `finalizer()` wraps a reconcile function so that it manages one finalizer for you, and tells it whether to apply the object or clean it up.

## Usage

```python
from kubex.k8s.v1_35.core.v1.config_map import ConfigMap
from kubex_runtime import (
    Action,
    FinalizerApply,
    FinalizerCleanup,
    FinalizerEvent,
    finalizer,
)

FINALIZER = "example.com/cleanup"


async def reconcile(cm: ConfigMap, ctx: Context) -> Action:
    async def handle(event: FinalizerEvent[ConfigMap]) -> Action:
        match event:
            case FinalizerApply(obj):
                await ensure_bucket(obj)
                return Action.requeue(300)
            case FinalizerCleanup(obj):
                await delete_bucket(obj)
                return Action.await_change()

    return await finalizer(ctx.api, FINALIZER, cm, handle)
```

`finalizer(api, finalizer_name, obj, reconcile)` looks at `obj` and does one of four things:

| Finalizer on the object | Being deleted | `finalizer()` |
|---|---|---|
| No | No | Adds the finalizer and returns `Action.await_change()`, without calling `reconcile`. The patch is a change to the object, so it triggers the next reconcile |
| Yes | No | Calls `reconcile(FinalizerApply(obj))` and returns its action |
| Yes | Yes | Calls `reconcile(FinalizerCleanup(obj))`, then removes the finalizer and returns the action |
| No | Yes | Nothing is left to do. Returns `Action.await_change()` |

`api` is an `Api` for the object's kind; only its `patch()` method is used, and every patch goes to the object's own namespace. An object without a name raises `FinalizerError`.

## Cleanup

The finalizer is removed as soon as the `FinalizerCleanup` branch returns, and the API server can then delete the object (unless other finalizers still hold it). So return only once the cleanup is complete. To try again later, raise: the error goes to the controller's error policy, which decides when to retry.

## Concurrent changes

The patches are JSON patches with guards, so they never do the wrong thing when the object changes in the meantime:

- Every patch tests the object's uid, so it never lands on another object re-created under the same name.
- Adding the finalizer tests the finalizer list it was computed from. The API server does not deduplicate finalizers, so this keeps two writers from both adding it.
- Removing the finalizer tests that it is still at the index where it was found.

A concurrent change makes the patch fail with `UnprocessableEntity` (422) instead of corrupting the list. The error goes to the error policy, and the retry reads the newer state.

A patch that finds the object gone, a 404 that names the object, is not an error: the store had not seen the deletion yet. After a cleanup, `finalizer()` then returns the cleanup's action; when adding the finalizer, it returns `Action.await_change()`. Any other 404, such as one for a path the server does not serve because `api` is for another kind, is raised.

## Filtering triggers

`finalizer()` adds the finalizer and then waits for the change that brings, so the controller must see that change. A controller that filters its own objects on [`generation`](watcher.md#predicates) never sees it, because adding a finalizer leaves the generation alone. Include the finalizers in the filtered value:

```python
from collections.abc import Hashable

from kubex.k8s.v1_35.apps.v1.deployment import Deployment
from kubex_runtime import Controller, generation, predicate_filter


def generation_and_finalizers(obj: Deployment) -> Hashable | None:
    gen = generation(obj)
    # None always passes: a kind without a generation is never filtered
    return None if gen is None else (gen, tuple(obj.metadata.finalizers or ()))


controller = Controller.for_shared(
    Deployment,
    deployments,  # a SharedReflector[Deployment]
    adapt=lambda stream: predicate_filter(stream, generation_and_finalizers),
)
```

Keep the `None` case. For a kind without a generation, `generation()` returns `None`, which `predicate_filter` always lets through. A tuple around that `None` is a value like any other, so the filter would drop every later change that leaves the finalizers alone, the deletion included, and the cleanup would never run.

`Controller.for_shared()` and `adapt=` are described in [Several Controllers](shared-reflectors.md#filtering-triggers).
