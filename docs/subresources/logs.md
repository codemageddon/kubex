# Logs

The `logs` subresource lets you read or stream the stdout/stderr output of a container running inside a Pod.

## Availability

Only resources that implement the `HasLogs` marker interface expose `api.logs`. In practice this means `Pod`. Accessing `api.logs` on any other resource type raises `NotImplementedError` at runtime and resolves to `SubresourceNotAvailable` for the type-checker.

```python
from kubex.k8s.v1_35.core.v1.pod import Pod

pod_api.logs.get(...)  # OK: Pod has HasLogs

from kubex.k8s.v1_35.apps.v1.deployment import Deployment

deploy_api.logs.get(...)  # type error + runtime NotImplementedError
```

## Reading logs in one call

`api.logs.get()` fetches the current log buffer as a single string. Use it for short-lived containers or when tailing a fixed number of lines.

```python
from typing import cast

import anyio

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
        pod = await api.create(
            Pod(
                metadata=ObjectMetadata(generate_name="example-pod-"),
                spec=PodSpec(containers=[Container(name="example", image="nginx")]),
            ),
        )
        pod_name = cast(str, pod.metadata.name)
        await anyio.sleep(5)

        logs = await api.logs.get(pod_name)
        print(logs)

        await api.delete(pod_name)
```

### Options

All options are keyword-only:

| Option | Type | Description |
|--------|------|-------------|
| `container` | `str | None` | Container name — required when the Pod has more than one container |
| `tail_lines` | `int | None` | Return only the last N lines |
| `since_seconds` | `int | None` | Return logs newer than this many seconds |
| `previous` | `bool | None` | Return logs from the previously terminated container instance |
| `timestamps` | `bool | None` | Prefix each line with its RFC 3339 timestamp |
| `limit_bytes` | `int | None` | Cap response body size in bytes |
| `namespace` | `str | None | ...` | Override the `Api` instance namespace for this call |
| `request_timeout` | `Timeout | float | None | ...` | Override the client-level timeout for this call |

## Streaming logs

`api.logs.stream()` is an async generator that yields one decoded line per iteration. The Kubernetes API sets `follow=true` internally, so the stream continues until the container exits or the caller breaks out.

```python
async def consume_logs(api: Api[Pod], pod_name: str) -> None:
    async for line in api.logs.stream(pod_name):
        print(line)
```

Because `stream()` can run indefinitely, wrap it in a timeout for scripts:

```python
import anyio

async def timed_stream(api: Api[Pod], pod_name: str) -> None:
    with anyio.fail_after(30):
        async for line in api.logs.stream(pod_name):
            print(line)
```

`stream()` accepts the same options as `get()`.

## Multi-container pods

When a Pod runs more than one container you must specify `container=`:

```python
logs = await api.logs.get(pod_name, container="sidecar")

async for line in api.logs.stream(pod_name, container="main"):
    print(line)
```

Omitting `container` on a multi-container Pod produces a 400 error from the Kubernetes API.

## Previous container logs

Use `previous=True` to read logs from the most recent terminated container instance — useful for crash-loop debugging:

```python
logs = await api.logs.get(pod_name, previous=True, tail_lines=200)
```
