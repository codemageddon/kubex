<p align="center">
  <img src="assets/logo.png" alt="Kubex logo" width="180">
</p>

# Kubex

**Async-first Kubernetes client library for Python**, inspired by [kube.rs](https://kube.rs/). Built on Pydantic v2, async-runtime agnostic (asyncio and trio).

[Get Started](getting-started/installation.md){ .md-button .md-button--primary }
[GitHub](https://github.com/codemageddon/kubex){ .md-button }

---

## Why Kubex?

### Performance

Kubex is dramatically faster than [kubernetes-asyncio](https://github.com/tomplus/kubernetes_asyncio), the most popular async Kubernetes client for Python. Benchmarks against a K3s 1.35.4 cluster (see `benchmarks/`):

| Scenario | kubernetes-asyncio | kubex (aiohttp) | kubex (httpx) | Speedup |
|---|---|---|---|---|
| Single GET | 61 ms | 6 ms | 26 ms | **10×** |
| List 100 pods | 2,813 ms | 73 ms | 102 ms | **38×** |
| List 500 pods | 14,441 ms | 351 ms | 410 ms | **41×** |
| Watch 50 events | 3,957 ms | 562 ms | 1,764 ms | **7×** |

Kubex also uses **~47% less heap memory** and makes **up to ~5x fewer allocations**, reducing GC pressure in long-running controllers and operators.

### Fully typed

Every Kubernetes resource is a Pydantic v2 model with proper type annotations — spec fields, status fields, enums, and nested objects are all typed, not `dict[str, Any]`. Combined with `mypy --strict` support, you get IDE autocompletion and compile-time safety instead of runtime `KeyError`s.

```python
from kubex.api import Api
from kubex.client import create_client
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

---

## Quick example

```python
from kubex.api import Api
from kubex.client import create_client
from kubex.k8s.v1_35.core.v1.pod import Pod

async with await create_client() as client:
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    pods = await api.list()
    for pod in pods.items:
        print(pod.metadata.name, pod.status.phase)
```

---

## Next steps

- [Installation](getting-started/installation.md) — install Kubex and its optional extras
- [Quickstart](getting-started/quickstart.md) — connect to your cluster and make your first request
- [Concepts](concepts/index.md) — understand the API design, client model, and resource configuration
