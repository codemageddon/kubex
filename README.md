# Kubex

Kubex is a Kubernetes client library for Python inspired by kube.rs. It is built on top of [Pydantic](https://github.com/pydantic/pydantic) and is async-runtime agnostic.

# Why Kubex?

### Performance

Kubex is dramatically faster than [kubernetes-asyncio](https://github.com/tomplus/kubernetes_asyncio), the most popular async Kubernetes client for Python. Benchmarks against a K3s 1.35 cluster (see `benchmarks/`):

| Scenario | kubernetes-asyncio | kubex (aiohttp) | kubex (httpx) | Speedup |
|---|---|---|---|---|
| Single GET | 60 ms | 6 ms | 28 ms | **10x** |
| List 100 pods | 2,783 ms | 74 ms | 102 ms | **37x** |
| List 500 pods | 14,167 ms | 351 ms | 409 ms | **40x** |
| Watch 50 events | 3,856 ms | 635 ms | 1,914 ms | **6x** |

Kubex also uses **49% less heap memory** and makes **up to 5x fewer allocations**, reducing GC pressure in long-running controllers and operators.

### Fully typed

Every Kubernetes resource is a Pydantic v2 model with proper type annotations — spec fields, status fields, enums, and nested objects are all typed, not `dict[str, Any]`. Combined with `mypy --strict` support, you get IDE autocompletion and compile-time safety instead of runtime KeyErrors.

```python
from kubex import Api, create_client
from kubex.k8s.v1_35.core.v1.pod import Pod

async with await create_client() as client:
    api: Api[Pod] = Api(Pod, client=client)
    pod = await api.get("my-pod", namespace="default")
    # pod.spec, pod.status, pod.metadata are all fully typed
```

### Multi-version Kubernetes support

Kubex ships separate model packages for Kubernetes 1.32 through 1.37. You can depend on exactly the versions you need, or use multiple versions simultaneously — useful when managing clusters at different upgrade stages:

```python
from kubex.k8s.v1_34.apps.v1.deployment import Deployment as Deployment134
from kubex.k8s.v1_35.apps.v1.deployment import Deployment as Deployment135
```

Each package is generated from the official OpenAPI spec, so models always match the wire schema of the target cluster.

### Async-runtime agnostic

Kubex works with both **asyncio** and **trio** (via httpx), with no framework lock-in.

# Completed Features:

* Basic API interface that allows interaction with almost any Kubernetes resources and their methods.
* In-cluster client authorization with token refreshing.
* Basic support for kubeconfig files.
* `httpx` and `aiohttp` as an underlying http-client support.
* `asyncio` and `trio` async runtime support (only `httpx` client is supported for `trio`).
* Comprehensive, fully-typed Kubernetes resource models (1.32–1.37) generated from the OpenAPI spec via a built-in code generator.

# Planned Features:

* [ ] Support for OIDC and other authentication extensions.
* [x] Fine-tuning of timeouts.
* [ ] Dynamic API object creation to exclude unsupported methods for resources (requires research for mypy compatibility).
* [ ] Potential synchronous version of the client.
* [ ] Additional tests and examples.
* [x] JsonPatch models.
* [ ] Enhanced support for subresources (status, ephemeral containers).
* [ ] Support for Pod.attach.
