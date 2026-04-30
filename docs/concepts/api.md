# Api[T]

`Api[ResourceType]` is the central class in Kubex. Every operation — get, list, create, delete, watch, patch — goes through it.

## Creating an Api instance

```python
from kubex.api import Api
from kubex.client import create_client
from kubex.k8s.v1_35.core.v1.pod import Pod

client = await create_client()
api: Api[Pod] = Api(Pod, client=client, namespace="default")
```

The type parameter (`Pod` here) is resolved at construction time and binds the return types of every method. Your IDE and mypy can infer that `api.get(...)` returns a `Pod`, `api.list(...)` returns a `ListEntity[Pod]`, and so on.

### Using `create_api()`

`create_api()` is a convenience factory that creates both a client and an `Api` in one call:

```python
from kubex.api import create_api
from kubex.k8s.v1_35.core.v1.pod import Pod

api = await create_api(Pod, namespace="default")
```

If you already have a `BaseClient` instance you want to reuse across multiple resource types, pass it explicitly:

```python
client = await create_client()
pod_api = await create_api(Pod, client=client, namespace="default")
deploy_api = await create_api(Deployment, client=client, namespace="default")
```

## Namespace vs cluster scope

Kubernetes resources are either **namespace-scoped** (Pods, Deployments, Services, …) or **cluster-scoped** (Namespaces, ClusterRoles, Nodes, …).

Kubex enforces this at the model level. When you create an `Api[Pod]`, the library knows `Pod` is namespace-scoped and will raise an error if you pass a namespace to a cluster-scoped resource's method.

### Setting a default namespace

Pass `namespace=` to the `Api` constructor to set a default for every method call:

```python
api: Api[Pod] = Api(Pod, client=client, namespace="production")
pod = await api.get("web-server")  # uses "production"
```

### Overriding the namespace per-call

Any method that accepts a namespace argument lets you override the default:

```python
pod = await api.get("web-server", namespace="staging")
```

### The Ellipsis sentinel

The namespace parameter on every method defaults to `...` (Ellipsis), not `None`. This distinction matters:

| Value | Meaning |
|---|---|
| `...` (Ellipsis, the default) | Use the namespace set on the `Api` instance |
| `None` | Explicitly no namespace (cluster-scoped query or all-namespaces list) |
| `"my-namespace"` | Use this specific namespace for this call |

This is why you can pass `namespace=None` to list across all namespaces even when the `Api` has a default namespace set.

```python
# List pods in all namespaces, even though api was created with namespace="default"
pods = await api.list(namespace=None)
```

## Timeout overrides

Like namespace, the `request_timeout` parameter on every method defaults to `...` (Ellipsis), meaning "use the client-level default." Pass `None` to disable timeouts for a specific call (useful for long-running watch streams), or pass a number (seconds) for a per-call override:

```python
# Disable timeout for a long-running list
big_list = await api.list(request_timeout=None)

# Override to 5 seconds for this call only
pod = await api.get("my-pod", request_timeout=5)
```

See [Timeouts](../operations/timeouts.md) for full details.

## Subresource access

Subresources (logs, exec, portforward, scale, …) are accessed as attributes on the `Api` instance. They are only available when the resource type declares the appropriate marker interface:

```python
# Pod supports logs — this works
await pod_api.logs.get("my-pod")

# Deployment does not support logs — mypy error + runtime NotImplementedError
await deploy_api.logs.get("my-deploy")  # type: ignore[attr-defined]
```

See [Subresources](subresources.md) for details on the descriptor pattern and marker interfaces.
