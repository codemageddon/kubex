# Quickstart

This guide shows how to connect to a Kubernetes cluster and make your first request with Kubex.

## Prerequisites

Install Kubex with an HTTP client and Kubernetes model package:

```shell
pip install "kubex[aiohttp,k8s-1.35]"
```

See [Installation](installation.md) for the full extras matrix.

## Auto-detecting the cluster

`create_client()` resolves the cluster configuration automatically:

```python
from kubex.client import create_client

async with await create_client() as client:
    # ready to use
```

| Scenario | Resolution |
|---|---|
| `~/.kube/config` exists | Reads kubeconfig and uses the current context |
| `KUBECONFIG` env variable | Uses that file path |
| Running in a pod | Reads the service account token mounted at `/var/run/secrets/kubernetes.io/serviceaccount/` |

See [Configuration](../concepts/configuration.md) for kubeconfig file handling and in-cluster auth details.

## List namespaces

```python
from kubex.api import Api
from kubex.client import create_client
from kubex.k8s.v1_35.core.v1.namespace import Namespace


async def main() -> None:
    client = await create_client()
    async with client:
        api: Api[Namespace] = Api(Namespace, client=client)
        namespaces = await api.list()
        print(namespaces)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
```

## Create, inspect, and delete a Pod

```python
from kubex.api import Api
from kubex.client import create_client
from kubex.k8s.v1_35.core.v1.container import Container
from kubex.k8s.v1_35.core.v1.pod import Pod
from kubex.k8s.v1_35.core.v1.pod_spec import PodSpec
from kubex_core.models.metadata import ObjectMetadata

NAMESPACE = "default"


async def main() -> None:
    client = await create_client()
    async with client:
        api: Api[Pod] = Api(Pod, client=client, namespace=NAMESPACE)
        pod = await api.create(
            Pod(
                metadata=ObjectMetadata(generate_name="example-pod-"),
                spec=PodSpec(containers=[Container(name="example", image="nginx")]),
            ),
        )
        assert pod.metadata.name is not None

        try:
            print(pod)
            print(await api.metadata.get(pod.metadata.name))
            print(await api.metadata.list())
        finally:
            await api.delete(pod.metadata.name)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
```

!!! note
    All Kubernetes resources are fully typed Pydantic models. `pod.spec`, `pod.status`, and `pod.metadata` all have proper type annotations — no `dict[str, Any]` anywhere.

## What's next

- [Concepts: Api\[T\]](../concepts/api.md) — generics, namespace/cluster scope, the `Ellipsis` sentinel
- [Concepts: Configuration](../concepts/configuration.md) — kubeconfig file parsing, in-cluster auth, exec provider
- [Operations: CRUD](../operations/crud.md) — get, list, create, replace, delete, delete_collection
- [Operations: Watch](../operations/watch.md) — streaming resource events
