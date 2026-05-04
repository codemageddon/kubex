# Subresources

This section covers all Kubernetes subresource APIs exposed by Kubex.

Subresource operations are accessed through typed descriptors on `Api[T]`. Each descriptor checks whether the resource type declares the required marker interface — available operations are enforced both at type-check time (mypy) and at runtime.

```python
from kubex.api import Api
from kubex.client import create_client
from kubex.k8s.v1_35.core.v1.pod import Pod
from kubex.k8s.v1_35.apps.v1.deployment import Deployment

async with await create_client() as client:
    pod_api: Api[Pod] = Api(Pod, client=client, namespace="default")
    deploy_api: Api[Deployment] = Api(Deployment, client=client, namespace="default")

    await pod_api.logs.get("my-pod")          # OK — Pod has HasLogs
    await deploy_api.scale.get("my-deploy")   # OK — Deployment has HasScaleSubresource
    await pod_api.scale.get("my-pod")         # runtime NotImplementedError + type error
```

See [Subresources](../concepts/subresources.md) in the Concepts section for a full explanation of the descriptor pattern and marker interfaces.

## Standard subresources

| Page | Accessor | Marker | Resources |
|------|----------|--------|-----------|
| [Logs](logs.md) | `api.logs` | `HasLogs` | Pod |
| [Metadata](metadata.md) | `api.metadata` | *(always available)* | All |
| [Scale](scale.md) | `api.scale` | `HasScaleSubresource` | Deployment, StatefulSet, ReplicaSet, ReplicationController |
| [Status](status.md) | `api.status` | `HasStatusSubresource` | Most workload resources |
| [Eviction](eviction.md) | `api.eviction` | `Evictable` | Pod |
| [Ephemeral Containers](ephemeral-containers.md) | `api.ephemeral_containers` | `HasEphemeralContainers` | Pod |
| [Resize](resize.md) | `api.resize` | `HasResize` | Pod |

## WebSocket subresources

These subresources open a bidirectional WebSocket connection to the kubelet for interactive or streaming operations.

!!! warning "Beta / experimental"
    WebSocket subresources (`exec`, `attach`, `portforward`) are functional and tested against K3S, but the underlying channel-protocol implementation is relatively new. The API may change between minor releases.

| Page | Accessor | Marker | Resources |
|------|----------|--------|-----------|
| [Exec](exec.md) | `api.exec` | `HasExec` | Pod |
| [Attach](attach.md) | `api.attach` | `HasAttach` | Pod |
| [Portforward](portforward.md) | `api.portforward` | `HasPortForward` | Pod |
