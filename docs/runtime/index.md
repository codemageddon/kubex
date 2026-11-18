# Controller runtime

`kubex-runtime` provides the building blocks of Kubernetes controllers and operators on top of Kubex. It is a port of [kube-runtime](https://docs.rs/kube-runtime) from kube.rs. It runs on asyncio and on trio (through anyio), and on free-threaded Python.

!!! warning "Alpha"
    `kubex-runtime` is a separate package, versioned independently of `kubex`, and it is alpha: its API may change in any release.

## Install

=== "uv"

    ```shell
    uv add kubex-runtime
    ```

=== "pip"

    ```shell
    pip install kubex-runtime
    ```

`kubex-runtime` depends on `kubex` but pulls in no HTTP client and no model package. Install those too, as described in [Installation](../getting-started/installation.md):

```shell
uv add kubex-runtime "kubex[aiohttp,k8s-1.35]"
```

## Building blocks

| Piece | What it does | Page |
|---|---|---|
| `watcher()` | Watches one kind of object as an endless stream of events: the current objects, then their changes. It fetches the objects again when the resourceVersion expires and retries failures with a backoff | [Watcher](watcher.md) |
| `reflector()`, `Store`, `Writer` | Keeps an in-memory cache of those objects up to date and sends its changes to subscribers | [Reflectors & Stores](reflector.md) |
| `Controller` | Calls a reconcile function for every object that changed, or whose owned or watched objects changed, and requeues it when the function asks | [Controller](controller.md) |
| `finalizer()` | Runs cleanup before an object is deleted | [Finalizers](finalizer.md) |
| `SharedReflector` | One watch and one store, shared by several controllers | [Several Controllers](shared-reflectors.md) |

Each layer builds on the one below it. A controller feeds a watcher through a reflector into its store, and reads the objects it reconciles from that store. Each piece also works on its own: use a watcher when all you need is the events, and a reflector when you need a cache.

## A first controller

```python
from dataclasses import dataclass

import anyio

from kubex.api import Api
from kubex.client import create_client
from kubex.k8s.v1_35.core.v1.config_map import ConfigMap
from kubex_runtime import Action, Controller


@dataclass
class Context:
    api: Api[ConfigMap]


async def reconcile(cm: ConfigMap, ctx: Context) -> Action:
    print("reconciling", cm.metadata.namespace, cm.metadata.name)
    return Action.requeue(300)


def error_policy(cm: ConfigMap, error: Exception, ctx: Context) -> Action:
    return Action.requeue(5)


async def main() -> None:
    async with await create_client() as client:
        api: Api[ConfigMap] = Api(ConfigMap, client=client, namespace="default")
        await Controller(ConfigMap, api).run(reconcile, error_policy, Context(api))


anyio.run(main)
```

What this does:

- The controller lists the ConfigMaps in `default`, then watches them.
- Once the list has been loaded, it reconciles every ConfigMap, and then again on every change.
- `Action.requeue(300)` reconciles the object again in five minutes, unless a change comes first. `Action.await_change()` waits for the next change only.
- When a reconcile raises, the exception goes to `error_policy`, and the action it returns says when to retry.
- `run()` runs until it is cancelled and logs every failed reconcile.

The watch covers the `Api`'s namespace: pass `namespace=None` to watch every namespace. If you omit `namespace`, the `Api` uses the client's namespace: the kubeconfig context's namespace (`default` if the context sets none), or the pod's own namespace when running in a cluster. See [Api\[T\]](../concepts/api.md#setting-a-default-namespace).
