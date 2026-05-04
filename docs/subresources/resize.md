# Resize

The `resize` subresource allows you to change the CPU and memory resource requests and limits of a running Pod's containers in-place, without restarting the Pod. This is the Kubernetes [In-Place Pod Vertical Scaling](https://kubernetes.io/docs/tasks/configure-pod-container/resize-container-resources/) feature.

!!! note "Kubernetes version requirement"
    In-place resize is stable in Kubernetes 1.33. Earlier versions require the `InPlacePodVerticalScaling` feature gate to be enabled.

## Availability

Only resources with the `HasResize` marker interface expose `api.resize`. In practice this means `Pod`.

```python
from kubex.k8s.v1_35.core.v1.pod import Pod

pod_api.resize.get(...)   # OK

from kubex.k8s.v1_35.apps.v1.deployment import Deployment

deploy_api.resize.get(...)  # type error + runtime NotImplementedError
```

## Reading the current resource allocation

`api.resize.get()` returns the full `Pod` object. The relevant fields for in-place resize are `spec.containers[*].resources` and the corresponding `status.containerStatuses[*].resources` (which reflects what the kubelet has actually applied).

```python
from kubex.api import Api
from kubex.client import create_client
from kubex.k8s.v1_35.core.v1.pod import Pod


async def main() -> None:
    client = await create_client()
    async with client:
        api: Api[Pod] = Api(Pod, client=client, namespace="default")

        pod = await api.resize.get("my-pod")
        for container in pod.spec.containers:
            resources = container.resources
            if resources:
                print(f"{container.name}: requests={resources.requests}, limits={resources.limits}")
```

## Replacing resource allocation

`api.resize.replace()` is the primary write path. Retrieve the pod, update `spec.containers[*].resources`, then write it back:

```python
from typing import cast

from kubex.api import Api
from kubex.client import create_client
from kubex.k8s.v1_35.core.v1.pod import Pod
from kubex.k8s.v1_35.core.v1.resource_requirements import ResourceRequirements


async def resize_pod(pod_name: str) -> None:
    client = await create_client()
    async with client:
        api: Api[Pod] = Api(Pod, client=client, namespace="default")

        pod = await api.resize.get(pod_name)

        for container in pod.spec.containers:
            if container.name == "main":
                container.resources = ResourceRequirements(
                    requests={"cpu": "500m", "memory": "256Mi"},
                    limits={"cpu": "1", "memory": "512Mi"},
                )

        updated = await api.resize.replace(pod_name, pod)
        for c in updated.spec.containers:
            print(f"{c.name}: {c.resources}")
```

### Replace options

| Option | Type | Description |
|--------|------|-------------|
| `dry_run` | `DryRun | bool | None` | Validate without persisting |
| `field_manager` | `str | None` | Field manager name |
| `namespace` | `str | None | ...` | Override the `Api` instance namespace |
| `request_timeout` | `Timeout | float | None | ...` | Override the client-level timeout |

## Patching resource allocation

`api.resize.patch()` applies a partial update. `MergePatch` is the natural fit for targeting specific containers:

```python
from kubex.core.patch import MergePatch

updated = await api.resize.patch(
    "my-pod",
    MergePatch({
        "spec": {
            "containers": [
                {
                    "name": "main",
                    "resources": {
                        "requests": {"cpu": "500m", "memory": "256Mi"},
                        "limits": {"cpu": "1", "memory": "512Mi"},
                    },
                }
            ]
        }
    }),
)
```

`JsonPatch` is also accepted — it lets you replace a single nested field without re-sending the rest of the container spec:

```python
from kubex.core.patch import JsonPatch

# Bump main container memory request to 256Mi (containers[0] = "main")
updated = await api.resize.patch(
    "my-pod",
    JsonPatch().replace("/spec/containers/0/resources/requests/memory", "256Mi"),
)
```

`patch()` accepts the same options as `replace()` plus `force` and `field_validation` for server-side apply.

## Checking resize status

After a replace or patch the kubelet may take some time to apply the new resources. Check `status.containerStatuses[*].resources` to see the currently active allocation. The `status.resize` field (when present) indicates whether the resize is `Proposed`, `InProgress`, `Deferred`, or `Infeasible`:

```python
pod = await api.resize.get(pod_name)
for cs in (pod.status.container_statuses or []):
    print(f"{cs.name}: allocated={cs.resources}")
```

!!! tip
    A resize is `Deferred` when the node has insufficient capacity at the moment. The kubelet will apply it automatically once resources become available — no retry is needed from your side.
