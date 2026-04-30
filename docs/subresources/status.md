# Status

The `status` subresource provides isolated read/write access to a resource's `.status` field. Controllers and operators use it to update observed state without inadvertently modifying user-managed spec fields.

## Availability

Only resources with the `HasStatusSubresource` marker interface expose `api.status`. Most workload resources implement it: `Deployment`, `StatefulSet`, `DaemonSet`, `ReplicaSet`, `Job`, `CronJob`, `Pod`, `Node`, `Namespace`, and many more.

```python
from kubex.k8s.v1_35.apps.v1.deployment import Deployment

deploy_api.status.get(...)   # OK: Deployment has HasStatusSubresource

from kubex.k8s.v1_35.core.v1.config_map import ConfigMap

cm_api.status.get(...)       # type error + runtime NotImplementedError
```

## Reading status

`api.status.get()` returns the full resource object. The returned object contains the current `.status` field populated by the control plane. The `.spec` is also present, but write operations via this subresource only persist changes to `.status`.

```python
from kubex.api import Api
from kubex.client import create_client
from kubex.k8s.v1_35.apps.v1.deployment import Deployment


async def main() -> None:
    client = await create_client()
    async with client:
        api: Api[Deployment] = Api(Deployment, client=client, namespace="default")

        current = await api.status.get("my-deployment")
        print(
            f"Status: replicas={current.status and current.status.replicas}, "
            f"available={current.status and current.status.available_replicas}"
        )
```

## Replacing status

`api.status.replace()` writes a new status. Only `.status` is persisted — changes to `.spec` in the submitted object are silently ignored by the Kubernetes API.

This pattern is typical for controllers: read the current object, compute the new status, write it back:

```python
from typing import cast

from kubex.api import Api
from kubex.client import create_client
from kubex.k8s.v1_35.apps.v1.deployment import Deployment
from kubex.k8s.v1_35.apps.v1.deployment_spec import DeploymentSpec
from kubex.k8s.v1_35.apps.v1.deployment_status import DeploymentStatus
from kubex.k8s.v1_35.core.v1.container import Container
from kubex.k8s.v1_35.core.v1.pod_spec import PodSpec
from kubex.k8s.v1_35.core.v1.pod_template_spec import PodTemplateSpec
from kubex.k8s.v1_35.meta.v1.label_selector import LabelSelector
from kubex_core.models.metadata import ObjectMetadata


async def main() -> None:
    client = await create_client()
    async with client:
        api: Api[Deployment] = Api(Deployment, client=client, namespace="default")

        deployment = await api.create(
            Deployment(
                metadata=ObjectMetadata(
                    name="example-status",
                    labels={"app": "example-status"},
                ),
                spec=DeploymentSpec(
                    replicas=1,
                    selector=LabelSelector(match_labels={"app": "example-status"}),
                    template=PodTemplateSpec(
                        metadata=ObjectMetadata(labels={"app": "example-status"}),
                        spec=PodSpec(
                            containers=[Container(name="nginx", image="nginx:latest")],
                        ),
                    ),
                ),
            ),
        )
        name = cast(str, deployment.metadata.name)

        try:
            current = await api.status.get(name)
            print(
                f"Status: replicas={current.status and current.status.replicas}, "
                f"available={current.status and current.status.available_replicas}"
            )

            current.status = DeploymentStatus(replicas=1, available_replicas=1)
            updated = await api.status.replace(name, current)
            print(
                f"After replace: "
                f"replicas={updated.status and updated.status.replicas}, "
                f"available={updated.status and updated.status.available_replicas}"
            )
        finally:
            await api.delete(name)
```

### Replace options

| Option | Type | Description |
|--------|------|-------------|
| `dry_run` | `DryRun | bool | None` | Validate without persisting |
| `field_manager` | `str | None` | Field manager name |
| `namespace` | `str | None | ...` | Override the `Api` instance namespace |
| `request_timeout` | `Timeout | float | None | ...` | Override the client-level timeout |

## Patching status

`api.status.patch()` applies a partial status update. Only the fields present in the patch body are merged into `.status`. `MergePatch` is usually the right choice for status updates:

```python
from kubex.core.patch import MergePatch

updated = await api.status.patch(
    "my-deployment",
    MergePatch({"status": {"availableReplicas": 3}}),
)
```

`JsonPatch` is also accepted for operation-level control (e.g., conditional updates with `test`):

```python
from kubex.core.patch import JsonPatch

updated = await api.status.patch(
    "my-deployment",
    JsonPatch().replace("/status/availableReplicas", 3),
)
```

For server-side apply on status, use `ApplyPatch` with `force=True` and a `field_manager`:

```python
from kubex.core.patch import ApplyPatch

updated = await api.status.patch(
    "my-deployment",
    ApplyPatch({"status": {"conditions": [...]}}),
    force=True,
    field_manager="my-controller",
)
```

`patch()` accepts the same options as `replace()` plus `force` and `field_validation`.

## Status vs spec updates

Kubernetes splits resource management into two separate write paths:

- Write to the resource itself (via `api.replace()` or `api.patch()`) to update **spec** — user intent.
- Write via `api.status.replace()` or `api.status.patch()` to update **status** — observed state.

RBAC rules can be configured to allow a controller to write status without being able to modify spec, and vice versa. Keeping the two paths separate also prevents accidental spec overwrites when a controller only intends to report progress.
