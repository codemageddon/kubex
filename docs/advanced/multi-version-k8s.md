# Multi-version Kubernetes

Kubex ships a separate model package for each supported Kubernetes minor version. This lets you pin the exact API surface you target and use multiple versions in the same application.

## Available packages

| Package | K8s version | Install extra |
|---|---|---|
| `kubex-k8s-1-32` | 1.32 | `kubex[k8s-1.32]` |
| `kubex-k8s-1-33` | 1.33 | `kubex[k8s-1.33]` |
| `kubex-k8s-1-34` | 1.34 | `kubex[k8s-1.34]` |
| `kubex-k8s-1-35` | 1.35 | `kubex[k8s-1.35]` |
| `kubex-k8s-1-36` | 1.36 | `kubex[k8s-1.36]` |
| `kubex-k8s-1-37` | 1.37 | `kubex[k8s-1.37]` |

Each package is generated from the official Kubernetes OpenAPI spec, so models exactly match the wire schema of the target cluster.

## Picking a version

Install the package that matches your cluster:

```bash
pip install "kubex[httpx,k8s-1.35]"
```

Then import resources from that version's namespace:

```python
from kubex.k8s.v1_35.core.v1.pod import Pod
from kubex.k8s.v1_35.apps.v1.deployment import Deployment
from kubex.k8s.v1_35.batch.v1.job import Job
```

## Using multiple versions in one application

If your application manages clusters at different Kubernetes versions, you can import from multiple packages simultaneously. Python namespaces do not conflict — each version lives under its own `kubex.k8s.v1_NN` subpackage.

```python
from kubex.k8s.v1_34.apps.v1.deployment import Deployment as Deployment134
from kubex.k8s.v1_35.apps.v1.deployment import Deployment as Deployment135

async with await create_client(config_for_cluster_34) as client34:
    api34 = Api(Deployment134, client=client34, namespace="default")
    deploy = await api34.get("my-app")

async with await create_client(config_for_cluster_35) as client35:
    api35 = Api(Deployment135, client=client35, namespace="default")
    deploy = await api35.get("my-app")
```

## Installing multiple version packages

You can install multiple extras at once:

```bash
pip install "kubex[httpx,k8s-1.34,k8s-1.35]"
```

Or with `uv`:

```bash
uv add "kubex[httpx,k8s-1.34,k8s-1.35]"
```

## API compatibility across versions

Most Kubernetes APIs are stable across minor versions. Fields added in newer versions are `None` by default in older models, so code written against 1.34 models generally works unchanged against a 1.35 cluster. Fields removed between versions will surface as validation warnings or be silently dropped depending on Pydantic's model configuration.

For strict compatibility, always match the model package version to your cluster version.

## OpenAPI spec correspondence

Each model package is generated from the official `swagger.json` (OpenAPI v2) spec published with each Kubernetes release. The generator maps every OpenAPI schema to a Pydantic v2 model with proper field types — no `dict[str, Any]` catch-alls. Marker interfaces (`HasLogs`, `HasExec`, etc.) are added based on which subresource endpoints exist in the spec for that version.
