# Eviction

The `eviction` subresource triggers graceful pod termination while respecting [PodDisruptionBudgets](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/). It is the mechanism behind `kubectl drain` and is preferred over calling `api.delete()` directly when you need disruption-budget-aware eviction.

## Availability

Only resources with the `Evictable` marker interface expose `api.eviction`. In practice this means `Pod`.

```python
from kubex.k8s.v1_35.core.v1.pod import Pod

pod_api.eviction.create(...)   # OK: Pod has Evictable

from kubex.k8s.v1_35.apps.v1.deployment import Deployment

deploy_api.eviction.create(...)  # type error + runtime NotImplementedError
```

## Creating an eviction

`api.eviction.create()` submits an `Eviction` object to the API server. If the pod is protected by a `PodDisruptionBudget` that would be violated, the API server returns `429 Too Many Requests` and you should retry after a delay.

```python
from kubex.api import Api
from kubex.client import create_client
from kubex.core.exceptions import KubexApiError
from kubex.k8s.v1_35.core.v1.pod import Pod
from kubex_core.models.eviction import Eviction
from kubex_core.models.metadata import ObjectMetadata
from kubex_core.models.status import Status


async def evict_pod(pod_name: str, namespace: str) -> None:
    client = await create_client()
    async with client:
        api: Api[Pod] = Api(Pod, client=client, namespace=namespace)

        eviction = Eviction(
            metadata=ObjectMetadata(name=pod_name, namespace=namespace),
        )
        status: Status = await api.eviction.create(pod_name, eviction)
        print(f"Eviction status: {status.status}")
```

## Handling PodDisruptionBudget violations

When a PDB blocks the eviction the API server responds with HTTP 429. Kubex surfaces this as a `KubexApiError`. Retry with an exponential back-off until the PDB allows the eviction:

```python
import anyio

from kubex.core.exceptions import KubexApiError
from kubex_core.models.eviction import Eviction
from kubex_core.models.metadata import ObjectMetadata


async def evict_with_retry(api: Api[Pod], pod_name: str, namespace: str) -> None:
    eviction = Eviction(
        metadata=ObjectMetadata(name=pod_name, namespace=namespace),
    )
    for attempt in range(10):
        try:
            await api.eviction.create(pod_name, eviction)
            return
        except KubexApiError as exc:
            if exc.status.value == 429:
                await anyio.sleep(2**attempt)
            else:
                raise
    raise RuntimeError(f"Could not evict {pod_name} after 10 attempts")
```

## Options

| Option | Type | Description |
|--------|------|-------------|
| `dry_run` | `DryRun | bool | None` | Validate without performing the eviction |
| `field_manager` | `str | None` | Field manager name |
| `namespace` | `str | None | ...` | Override the `Api` instance namespace |
| `request_timeout` | `Timeout | float | None | ...` | Override the client-level timeout |

## Eviction vs deletion

| | `api.delete()` | `api.eviction.create()` |
|---|---|---|
| Respects PodDisruptionBudgets | No | Yes |
| Returns 429 when PDB blocks | No | Yes |
| Kubernetes mechanism | DELETE on the pod | POST to the eviction subresource |
| Typical use | Force removal | Graceful drain |

Use `api.delete()` only when you need to forcibly remove a pod regardless of PDBs (for example, during cluster decommission). Use eviction for controlled workload migrations.
