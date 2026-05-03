# Custom Resources

Custom Resources extend the Kubernetes API with your own resource types, defined by a [CustomResourceDefinition (CRD)](https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/). Kubex supports them the same way it supports built-in resources: you define a Pydantic model and pass it to `Api[T]`. No generated code, no special registry — just a class.

## Defining a CRD model

A custom resource model is a regular Pydantic class that inherits from a scope marker and declares `__RESOURCE_CONFIG__`:

```python
from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import Field

from kubex_core.models.base import BaseK8sModel
from kubex_core.models.interfaces import HasStatusSubresource, NamespaceScopedEntity
from kubex_core.models.resource_config import ResourceConfig, Scope


class WidgetSpec(BaseK8sModel):
    replicas: int = 1
    image: str = "nginx:latest"


class WidgetStatus(BaseK8sModel):
    ready_replicas: int | None = None


class Widget(NamespaceScopedEntity, HasStatusSubresource):
    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["Widget"]] = ResourceConfig(
        version="v1alpha1",
        kind="Widget",
        group="example.io",
        plural="widgets",
        scope=Scope.NAMESPACE,
    )
    api_version: Literal["example.io/v1alpha1"] = Field(
        default="example.io/v1alpha1",
        alias="apiVersion",
    )
    kind: Literal["Widget"] = Field(default="Widget")
    spec: WidgetSpec | None = None
    status: WidgetStatus | None = None
```

`ResourceConfig` arguments:

| Argument | Required | Description |
|---|---|---|
| `group` | no | API group, e.g. `"example.io"`; auto-derived from `api_version` Literal if omitted |
| `version` | no | API version, e.g. `"v1alpha1"`; auto-derived from `api_version` Literal if omitted |
| `kind` | no | Singular PascalCase kind, e.g. `"Widget"`; auto-derived from the `kind` field default if omitted |
| `plural` | no | Plural URL path segment; auto-derived from `kind` if omitted |
| `scope` | no | `Scope.NAMESPACE` (default) or `Scope.CLUSTER` |

`api_version` and `kind` fields use `Literal` types so Pydantic serializes them as fixed strings and mypy can verify type safety on API responses.

## Cluster-scoped CRDs

For cluster-scoped resources, inherit from `ClusterScopedEntity` and set `scope=Scope.CLUSTER`:

```python
# Same imports as above, plus:
from kubex_core.models.interfaces import ClusterScopedEntity


class ClusterWidgetSpec(BaseK8sModel):
    description: str = ""


class ClusterWidget(ClusterScopedEntity):
    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["ClusterWidget"]] = ResourceConfig(
        version="v1alpha1",
        kind="ClusterWidget",
        group="example.io",
        plural="clusterwidgets",
        scope=Scope.CLUSTER,
    )
    api_version: Literal["example.io/v1alpha1"] = Field(
        default="example.io/v1alpha1",
        alias="apiVersion",
    )
    kind: Literal["ClusterWidget"] = Field(default="ClusterWidget")
    spec: ClusterWidgetSpec | None = None
```

Cluster-scoped resources do not accept a `namespace` argument on `Api`. Passing one raises a `ValueError` at construction time.

## Adding subresource support

Kubex subresource accessors (`api.status`, `api.scale`) are enabled by marker interfaces from `kubex_core.models.interfaces`. Add the marker to the class inheritance to unlock the corresponding accessor:

```python
from kubex_core.models.interfaces import HasStatusSubresource, NamespaceScopedEntity

class Widget(NamespaceScopedEntity, HasStatusSubresource):
    ...
```

For standard CRDs, only `HasStatusSubresource` and `HasScaleSubresource` are meaningful — the Kubernetes API server exposes `status` and `scale` subresources for CRDs that declare them in the CRD spec. The remaining markers are Pod-only and not available on custom resources. Adding them to a CRD model compiles and type-checks correctly, but the API server will return a `404` or `405` at runtime. `HasLogs`, `HasExec`, `HasAttach`, and `HasPortForward` are kubelet-proxied operations; `Evictable`, `HasEphemeralContainers`, and `HasResize` are ordinary API-server subresources that exist only for Pods.

Available markers:

| Marker | Accessor unlocked | CRD support |
|---|---|---|
| `HasStatusSubresource` | `api.status.get()`, `.replace()`, `.patch()` | Yes — requires `status: {}` in CRD spec |
| `HasScaleSubresource` | `api.scale.get()`, `.replace()`, `.patch()` | Yes — requires `scale:` in CRD spec |
| `HasLogs` | `api.logs.get()`, `.stream()` | No — Pod/kubelet only |
| `Evictable` | `api.eviction.create()` | No — Pod-only, not CRD-supported |
| `HasEphemeralContainers` | `api.ephemeral_containers.get()`, `.replace()`, `.patch()` | No — Pod-only, not CRD-supported |
| `HasResize` | `api.resize.get()`, `.replace()`, `.patch()` | No — Pod-only, not CRD-supported |
| `HasExec` | `api.exec.run()`, `.stream()` | No — Pod/kubelet only |
| `HasAttach` | `api.attach.stream()` | No — Pod/kubelet only |
| `HasPortForward` | `api.portforward.forward()`, `.listen()` | No — Pod/kubelet only |

Accessing an unregistered subresource on a model that lacks the marker raises `NotImplementedError` at runtime and resolves to `SubresourceNotAvailable` for type checkers.

## CRUD operations

Before running any operations, the CRD must be installed on the cluster. Without a `CustomResourceDefinition` object registered for `widgets.example.io`, the API server will return a `404 Not Found` on the first request. Apply the CRD manifest before running the code below — see the [Kubernetes CRD documentation](https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/) for how to create one.

Once the CRD is installed and the model is defined, use it exactly like any built-in resource:

```python
# Widget, WidgetSpec, WidgetStatus defined in the "Defining a CRD model" section above
from kubex.api import Api
from kubex.client import create_client
from kubex.core.patch import ApplyPatch
from kubex_core.models.metadata import ObjectMetadata

async def main() -> None:
    client = await create_client()
    async with client:
        api: Api[Widget] = Api(Widget, client=client, namespace="default")

        # Create
        widget = await api.create(
            Widget(
                metadata=ObjectMetadata(name="my-widget"),
                spec=WidgetSpec(replicas=2),
            )
        )

        # Get
        fetched = await api.get("my-widget")
        print(f"replicas={fetched.spec and fetched.spec.replicas}")

        # List
        widget_list = await api.list()
        print(f"{len(widget_list.items)} widget(s) found")

        # Server-side apply patch
        patched = await api.patch(
            "my-widget",
            ApplyPatch(
                Widget(
                    api_version="example.io/v1alpha1",
                    kind="Widget",
                    metadata=ObjectMetadata(name="my-widget"),
                    spec=WidgetSpec(replicas=3),
                )
            ),
            field_manager="my-controller",
            force=True,
        )
        print(f"patched replicas={patched.spec and patched.spec.replicas}")

        # Status subresource (requires HasStatusSubresource marker)
        status = await api.status.get("my-widget")
        print(f"ready={status.status and status.status.ready_replicas}")

        # Delete
        await api.delete("my-widget")
```

See `examples/custom_resource.py` in the repository for a complete runnable version. It requires a running cluster with both the `widgets.example.io` and `clusterwidgets.example.io` CRDs installed.

## Automatic pluralization

When `plural` is omitted from `ResourceConfig`, kubex derives it from `kind` at first access using simple English rules:

| Kind ends with | Rule | Example |
|---|---|---|
| `y` | replace `y` → `ies` | `Category` → `categories` |
| `s` or `x` | append `es` | `Ingress` → `ingresses` |
| anything else | append `s` | `Widget` → `widgets` |

Override `plural` explicitly when the CRD declares a plural that the auto-derivation rules would not produce — for example, a `FooInstance` resource whose CRD registers `plural: foo-instances` rather than the auto-derived `fooinstances`.
