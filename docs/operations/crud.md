# CRUD Operations

`Api[ResourceType]` exposes the full set of Kubernetes CRUD operations as `async` methods. Every method returns the server-side resource (or a `Status` for deletions), fully parsed by Pydantic.

## get

Fetch a single resource by name:

```python
from kubex.api import Api
from kubex.client import create_client
from kubex.k8s.v1_35.core.v1.pod import Pod

client = await create_client()
async with client:
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    pod = await api.get("my-pod")
    print(pod.metadata.name)
```

Pass `resource_version=` to pin the read to a specific version; omit it for the current state.

## list

List all resources in a namespace (or cluster-wide):

```python
pods = await api.list()
for pod in pods.items:
    print(pod.metadata.name)
```

Filter with `label_selector=` (e.g. `"app=nginx"`) or `field_selector=` (e.g. `"status.phase=Running"`). Use `limit=` and `continue_token=` for paginated results:

```python
page = await api.list(label_selector="app=nginx", limit=100)
while page.metadata.continue_:
    page = await api.list(label_selector="app=nginx", limit=100, continue_token=page.metadata.continue_)
```

Pass `namespace=None` to list across all namespaces even when the `Api` instance has a default namespace set:

```python
all_pods = await api.list(namespace=None)
```

## create

Create a new resource. The returned object is the server-assigned representation (including `metadata.name` when `generate_name` was used):

```python
from kubex.k8s.v1_35.core.v1.container import Container
from kubex.k8s.v1_35.core.v1.pod_spec import PodSpec
from kubex_core.models.metadata import ObjectMetadata

pod = await api.create(
    Pod(
        metadata=ObjectMetadata(generate_name="example-pod-"),
        spec=PodSpec(containers=[Container(name="example", image="nginx")]),
    ),
)
print(pod.metadata.name)  # server-assigned name, e.g. "example-pod-7g4k2"
```

Pass `dry_run=True` to validate the request without persisting anything. Pass `field_manager=` to set the field manager for server-side apply.

## replace

Replace a resource in its entirety (the get → modify → replace pattern):

```python
current = await api.get("example-pod")
current.metadata.labels = {**(current.metadata.labels or {}), "env": "staging"}
updated = await api.replace("example-pod", current)
print(updated.metadata.labels)
```

The full object (including `resourceVersion`) must be present in the payload — the API server uses `resourceVersion` as an optimistic-concurrency check.

## delete

Delete a resource by name. The return type is `Status | ResourceType`: if the resource has finalizers the API server returns the updated object (with `deletionTimestamp` set) rather than a `Status`:

```python
result = await api.delete("example-pod")
```

Control deletion behaviour with optional parameters:

| Parameter | Description |
|---|---|
| `grace_period_seconds` | Override the resource's `terminationGracePeriodSeconds` |
| `propagation_policy` | `"Foreground"`, `"Background"`, or `"Orphan"` |
| `preconditions` | `Precondition(uid=..., resource_version=...)` for safe deletes |
| `dry_run` | Validate without actually deleting |

```python
from kubex.core.params import Precondition

await api.delete(
    "example-pod",
    grace_period_seconds=0,
    propagation_policy="Foreground",
    preconditions=Precondition(uid=pod.metadata.uid),
)
```

## delete_collection

Delete multiple resources matching a selector in a single call:

```python
result = await api.delete_collection(label_selector="app=example-batch")
```

`delete_collection` accepts the same filter parameters as `list` (`label_selector`, `field_selector`, `limit`, `continue_token`) plus the same deletion options as `delete` (`grace_period_seconds`, `propagation_policy`, `preconditions`, `dry_run`).

The return type is `Status | ListEntity[ResourceType]` — some versions of the Kubernetes API return the deleted list rather than a `Status`.

Full example from `examples/delete_collection.py`:

```python
import uuid
from kubex.api import Api
from kubex.client import create_client
from kubex.k8s.v1_35.core.v1.container import Container
from kubex.k8s.v1_35.core.v1.pod import Pod
from kubex.k8s.v1_35.core.v1.pod_spec import PodSpec
from kubex_core.models.metadata import ObjectMetadata

async def main() -> None:
    client = await create_client()
    async with client:
        api: Api[Pod] = Api(Pod, client=client, namespace="default")
        run_id = uuid.uuid4().hex[:8]
        label_selector = f"app=example-batch-{run_id}"

        for i in range(3):
            await api.create(
                Pod(
                    metadata=ObjectMetadata(
                        generate_name=f"example-delete-collection-{i}-",
                        labels={"app": f"example-batch-{run_id}"},
                    ),
                    spec=PodSpec(containers=[Container(name="nginx", image="nginx:latest")]),
                ),
            )

        result = await api.delete_collection(label_selector=label_selector)
        print(f"delete_collection result: {type(result).__name__}")
```

## Error handling

All non-2xx responses raise a subclass of `KubexApiError`. The most common errors for CRUD operations:

| Exception | HTTP status | Typical cause |
|---|---|---|
| `NotFound` | 404 | Resource does not exist |
| `Conflict` | 409 | `create` on an existing resource, or `replace` with a stale `resourceVersion` |
| `Forbidden` | 403 | RBAC: the service account lacks permission |
| `UnprocessableEntity` | 422 | Validation failure (schema mismatch, required field missing) |

See [Exceptions](../concepts/exceptions.md) for the full hierarchy.
