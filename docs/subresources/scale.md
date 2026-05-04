# Scale

The `scale` subresource lets you read and update the replica count of scalable resources without modifying the full resource spec.

## Availability

Only resources with the `HasScaleSubresource` marker interface expose `api.scale`. This includes `Deployment`, `ReplicaSet`, `StatefulSet`, and `ReplicationController`. Accessing `api.scale` on a resource that does not have the marker raises `NotImplementedError` at runtime and is a type error for the type-checker.

```python
from kubex.k8s.v1_35.apps.v1.deployment import Deployment

deploy_api.scale.get(...)   # OK: Deployment has HasScaleSubresource

from kubex.k8s.v1_35.core.v1.pod import Pod

pod_api.scale.get(...)      # type error + runtime NotImplementedError
```

## Reading the current scale

`api.scale.get()` returns a `Scale` object with `spec.replicas` set to the current desired replica count and `status.replicas` reflecting the observed count.

```python
from typing import cast

from kubex.api import Api
from kubex.client import create_client
from kubex.k8s.v1_35.apps.v1.deployment import Deployment
from kubex_core.models.scale import Scale


async def main() -> None:
    client = await create_client()
    async with client:
        api: Api[Deployment] = Api(Deployment, client=client, namespace="default")

        scale: Scale = await api.scale.get("my-deployment")
        print(f"desired replicas: {scale.spec.replicas}")
        print(f"observed replicas: {scale.status.replicas}")
```

## Replacing the scale

`api.scale.replace()` is the canonical way to set a new replica count. Retrieve the current `Scale`, mutate `spec.replicas`, and write it back:

```python
from typing import cast

from kubex.api import Api
from kubex.client import create_client
from kubex.k8s.v1_35.apps.v1.deployment import Deployment
from kubex.k8s.v1_35.apps.v1.deployment_spec import DeploymentSpec
from kubex.k8s.v1_35.core.v1.container import Container
from kubex.k8s.v1_35.core.v1.pod_spec import PodSpec
from kubex.k8s.v1_35.core.v1.pod_template_spec import PodTemplateSpec
from kubex.k8s.v1_35.meta.v1.label_selector import LabelSelector
from kubex_core.models.metadata import ObjectMetadata
from kubex_core.models.scale import ScaleSpec


async def main() -> None:
    client = await create_client()
    async with client:
        api: Api[Deployment] = Api(Deployment, client=client, namespace="default")

        deployment = await api.create(
            Deployment(
                metadata=ObjectMetadata(
                    name="example-scale",
                    labels={"app": "example-scale"},
                ),
                spec=DeploymentSpec(
                    replicas=1,
                    selector=LabelSelector(match_labels={"app": "example-scale"}),
                    template=PodTemplateSpec(
                        metadata=ObjectMetadata(labels={"app": "example-scale"}),
                        spec=PodSpec(
                            containers=[Container(name="nginx", image="nginx:latest")],
                        ),
                    ),
                ),
            ),
        )
        name = cast(str, deployment.metadata.name)

        try:
            current_scale = await api.scale.get(name)
            print(f"Current replicas: {current_scale.spec.replicas}")

            current_scale.spec = ScaleSpec(replicas=3)
            updated_scale = await api.scale.replace(name, current_scale)
            print(f"Updated replicas: {updated_scale.spec.replicas}")

            final_scale = await api.scale.get(name)
            print(f"Confirmed replicas: {final_scale.spec.replicas}")
        finally:
            await api.delete(name)
```

### Replace options

| Option | Type | Description |
|--------|------|-------------|
| `dry_run` | `DryRun | bool | None` | Validate without persisting |
| `field_manager` | `str | None` | Field manager name |
| `namespace` | `str | None | ...` | Override the `Api` instance namespace |
| `request_timeout` | `Timeout | float | None | ...` | Override the client-level timeout |

## Patching the scale

Use `api.scale.patch()` when you want a partial update rather than a full replace. `MergePatch` is the natural choice for setting a value:

```python
from kubex.core.patch import MergePatch

updated = await api.scale.patch(
    "my-deployment",
    MergePatch({"spec": {"replicas": 5}}),
)
print(f"New desired replicas: {updated.spec.replicas}")
```

`JsonPatch` is also accepted — useful when you want operation-level control such as `test` for optimistic concurrency:

```python
from kubex.core.patch import JsonPatch

updated = await api.scale.patch(
    "my-deployment",
    JsonPatch().replace("/spec/replicas", 5),
)
```

`patch()` accepts the same options as `replace()` plus `force` and `field_validation` for server-side apply semantics.
