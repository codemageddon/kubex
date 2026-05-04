# Ephemeral Containers

Ephemeral containers are temporary containers that can be injected into a running Pod for debugging purposes. Unlike regular containers they are not defined at Pod creation time, cannot be restarted, and have no resource guarantees. They are most commonly used to attach a debug toolset to a Pod that runs a distroless or scratch image.

!!! note "Kubernetes version requirement"
    Ephemeral containers require Kubernetes 1.23 or later (stable since 1.25).

## Availability

Only resources with the `HasEphemeralContainers` marker interface expose `api.ephemeral_containers`. In practice this means `Pod`.

```python
from kubex.k8s.v1_35.core.v1.pod import Pod

pod_api.ephemeral_containers.get(...)   # OK

from kubex.k8s.v1_35.apps.v1.deployment import Deployment

deploy_api.ephemeral_containers.get(...)  # type error + runtime NotImplementedError
```

## Reading ephemeral containers

`api.ephemeral_containers.get()` returns the full `Pod` object with the `ephemeral_containers` field populated. The other spec fields are also present, but only `ephemeral_containers` can be modified via this subresource.

```python
from kubex.api import Api
from kubex.client import create_client
from kubex.k8s.v1_35.core.v1.pod import Pod


async def main() -> None:
    client = await create_client()
    async with client:
        api: Api[Pod] = Api(Pod, client=client, namespace="default")

        pod = await api.ephemeral_containers.get("my-pod")
        containers = pod.spec.ephemeral_containers or []
        for c in containers:
            print(c.name, c.image)
```

## Adding an ephemeral container

Retrieve the pod, append the new ephemeral container to `spec.ephemeral_containers`, then call `replace()`. Ephemeral containers can only be added — never removed or modified after creation.

```python
from typing import cast

from kubex.api import Api
from kubex.client import create_client
from kubex.k8s.v1_35.core.v1.ephemeral_container import EphemeralContainer
from kubex.k8s.v1_35.core.v1.pod import Pod


async def inject_debug_container(pod_name: str) -> None:
    client = await create_client()
    async with client:
        api: Api[Pod] = Api(Pod, client=client, namespace="default")

        pod = await api.ephemeral_containers.get(pod_name)

        existing = list(pod.spec.ephemeral_containers or [])
        existing.append(
            EphemeralContainer(
                name="debugger",
                image="busybox:latest",
                stdin=True,
                tty=True,
            )
        )
        pod.spec.ephemeral_containers = existing

        updated = await api.ephemeral_containers.replace(pod_name, pod)
        names = [c.name for c in (updated.spec.ephemeral_containers or [])]
        print(f"Ephemeral containers: {names}")
```

## Patching ephemeral containers

`api.ephemeral_containers.patch()` applies a partial update. Use it when you want to merge a new container entry without reserializing the entire pod:

```python
from kubex.core.patch import MergePatch

updated = await api.ephemeral_containers.patch(
    "my-pod",
    MergePatch({
        "spec": {
            "ephemeralContainers": [
                {"name": "debugger", "image": "busybox:latest", "stdin": True, "tty": True}
            ]
        }
    }),
)
```

`JsonPatch` is also accepted — useful when you want to append by index without re-sending the whole list:

```python
from kubex.core.patch import JsonPatch

updated = await api.ephemeral_containers.patch(
    "my-pod",
    JsonPatch().add(
        "/spec/ephemeralContainers/-",
        {"name": "debugger", "image": "busybox:latest", "stdin": True, "tty": True},
    ),
)
```

### Options for replace and patch

| Option | Type | Description |
|--------|------|-------------|
| `dry_run` | `DryRun | bool | None` | Validate without persisting |
| `field_manager` | `str | None` | Field manager name |
| `force` | `bool | None` | Force apply (patch only, for server-side apply) |
| `field_validation` | `FieldValidation | None` | Schema validation mode |
| `namespace` | `str | None | ...` | Override the `Api` instance namespace |
| `request_timeout` | `Timeout | float | None | ...` | Override the client-level timeout |

## Interacting with an ephemeral container

After adding the ephemeral container you can attach to it using the `exec` or `attach` subresources. Specify `container="debugger"` to target it explicitly:

```python
result = await api.exec.run(
    pod_name,
    command=["sh", "-c", "ls /proc/1/fd"],
    container="debugger",
)
print(result.stdout)
```

See [Exec](exec.md) and [Attach](attach.md) for full details.
