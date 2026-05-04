# Subresources

Kubernetes resources expose additional operations beyond CRUD through *subresources* — for example, reading logs, scaling a Deployment, or exec-ing into a Pod. Kubex models these as typed attributes on `Api[T]`, available only when the resource type supports them.

## Marker interfaces

Each subresource capability is declared as a marker class in `kubex_core.models.interfaces`. Resource models opt in by inheriting from the relevant markers:

| Marker class | Subresource | Example resources |
|---|---|---|
| `HasLogs` | `api.logs` | `Pod` |
| `HasStatusSubresource` | `api.status` | `Pod`, `Deployment`, `Service`, … |
| `HasScaleSubresource` | `api.scale` | `Deployment`, `StatefulSet`, `ReplicaSet` |
| `Evictable` | `api.eviction` | `Pod` |
| `HasEphemeralContainers` | `api.ephemeral_containers` | `Pod` |
| `HasResize` | `api.resize` | `Pod` |
| `HasExec` | `api.exec` | `Pod` |
| `HasAttach` | `api.attach` | `Pod` |
| `HasPortForward` | `api.portforward` | `Pod` |

A resource declares multiple capabilities through multiple inheritance:

```python
class Pod(
    NamespaceScopedEntity,
    HasLogs,
    HasStatusSubresource,
    Evictable,
    HasEphemeralContainers,
    HasResize,
    HasExec,
    HasAttach,
    HasPortForward,
):
    ...
```

## Type safety

Accessing a subresource the resource does not declare is a static type error and raises `NotImplementedError` at runtime — there is no silent fallback. Pick the right resource and the IDE/type-checker will guide you the rest of the way:

```python
pod_api: Api[Pod] = Api(Pod, client=client, namespace="default")
deploy_api: Api[Deployment] = Api(Deployment, client=client, namespace="default")

# OK — Pod has HasLogs
logs = await pod_api.logs.get("my-pod")

# Type error (mypy / pyright) + NotImplementedError at runtime — Deployment has no HasLogs
logs = await deploy_api.logs.get("my-deploy")
```

## Metadata accessor

`api.metadata` is always available regardless of the resource type. It provides lightweight read operations (`get`, `list`, `patch`, `watch`) that return partial metadata objects instead of full resources, saving bandwidth and parse time for large lists.

```python
meta = await api.metadata.get("my-pod")
metas = await api.metadata.list()
```

See [Metadata](../subresources/metadata.md) for full documentation.
