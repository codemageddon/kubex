# Patch

`api.patch(name, patch)` applies a partial update to an existing resource. Kubex supports all three patch strategies used by the Kubernetes API.

## Patch types

| Type | Import | `Content-Type` |
|---|---|---|
| `MergePatch` | `kubex.core.patch` | `application/merge-patch+json` |
| `StrategicMergePatch` | `kubex.core.patch` | `application/strategic-merge-patch+json` |
| `JsonPatch` | `kubex.core.patch` | `application/json-patch+json` |

## `MergePatch`

Merge patch (RFC 7396) replaces the specified keys and removes any key set to `null`. Keys not present in the patch are left unchanged. Wrap any resource model in `MergePatch(...)` to apply it:

```python
from kubex.core.patch import MergePatch
from kubex.k8s.v1_35.apps.v1.deployment import Deployment
from kubex.k8s.v1_35.apps.v1.deployment_spec import DeploymentSpec
from kubex.k8s.v1_35.meta.v1.label_selector import LabelSelector
from kubex.k8s.v1_35.core.v1.pod_spec import PodSpec
from kubex.k8s.v1_35.core.v1.pod_template_spec import PodTemplateSpec
from kubex.k8s.v1_35.core.v1.container import Container
from kubex_core.models.metadata import ObjectMetadata

merge_patch = MergePatch(
    Deployment(
        spec=DeploymentSpec(
            replicas=3,
            selector=LabelSelector(match_labels={"app": "example"}),
            template=PodTemplateSpec(
                metadata=ObjectMetadata(labels={"app": "example"}),
                spec=PodSpec(containers=[Container(name="nginx", image="nginx:latest")]),
            ),
        )
    )
)
patched = await api.patch("example-deploy", merge_patch)
print(patched.spec.replicas)  # 3
```

## `StrategicMergePatch`

Strategic merge patch is a Kubernetes extension that understands list-merging semantics (e.g., merging containers by name rather than replacing the whole array). Use it when you want to add or update a list element without specifying the full list:

```python
from kubex.core.patch import StrategicMergePatch

strategic_patch = StrategicMergePatch(
    Deployment(
        metadata=ObjectMetadata(
            annotations={"example.com/patched": "true"},
        )
    )
)
patched = await api.patch("example-deploy", strategic_patch)
print(patched.metadata.annotations)
```

Strategic merge patch is not available for custom resources — use `MergePatch` or `JsonPatch` there.

## `JsonPatch`

JSON Patch (RFC 6902) describes a sequence of operations (`add`, `remove`, `replace`, `move`, `copy`, `test`) using JSON Pointer paths. Build patches incrementally using the fluent API:

```python
from kubex.core.patch import JsonPatch

json_patch = JsonPatch().add("/metadata/labels/version", "v1")
patched = await api.patch("example-deploy", json_patch)
print(patched.metadata.labels)
```

All six RFC 6902 operations are supported:

```python
patch = (
    JsonPatch()
    .add("/metadata/labels/env", "staging")
    .replace("/spec/replicas", 2)
    .remove("/metadata/annotations/example.com~1old-key")
    .test("/metadata/name", "example-deploy")
)
```

### Building paths with `JsonPointer`

`JsonPointer` is accepted anywhere a path string is, and it handles RFC 6901 escaping for you. Build a pointer by chaining the `/` operator from a base, or from a tuple of unescaped tokens:

```python
from kubex.core.patch import JsonPatch, JsonPointer

# Chained operator — ideal when a fixed prefix is reused
annotation_path = JsonPointer("/metadata") / "annotations" / "example.com/patched"
# annotation_path == "/metadata/annotations/example.com~1patched"

patch = JsonPatch().add(annotation_path, "true")

# Or from raw tokens
label_path = JsonPointer.from_tokens("metadata", "labels", "version")
patch = patch.replace(label_path, "v2")
```

!!! note "JSON Pointer escaping"
    Per RFC 6901, `/` inside a key is escaped as `~1` and `~` is escaped as `~0`. For example, the annotation key `example.com/patched` becomes the path segment `example.com~1patched`.

    Kubex can do this for you — pass a `JsonPointer` instead of a raw string:
    `JsonPointer.from_tokens("metadata", "annotations", "example.com/patched")`
    or `JsonPointer("/metadata") / "annotations" / "example.com/patched"`. Both
    yield `/metadata/annotations/example.com~1patched` with the slash escaped
    automatically.

You can also construct a `JsonPatch` from a list of operation objects directly:

```python
from kubex.core.patch import JsonPatch
from kubex.core.json_patch import JsonPatchAdd, JsonPatchRemove

patch = JsonPatch([
    JsonPatchAdd(path="/metadata/labels/env", value="staging"),
    JsonPatchRemove(path="/metadata/labels/old-env"),
])
```

## Patch options

All three patch types accept these optional keyword arguments on `api.patch()`:

| Parameter | Description |
|---|---|
| `dry_run` | Validate without persisting (`True` or `DryRun.ALL`) |
| `field_manager` | Field manager name for server-side apply tracking |
| `force` | Force apply even when field ownership conflicts (server-side apply only) |
| `field_validation` | `FieldValidation.STRICT` (default), `WARN`, or `IGNORE` |

```python
patched = await api.patch(
    "example-deploy",
    merge_patch,
    dry_run=True,
    field_manager="my-controller",
)
```

## Full example from `examples/patch_deployment.py`

```python
from typing import cast

from kubex.api import Api
from kubex.client import create_client
from kubex.core.patch import JsonPatch, MergePatch, StrategicMergePatch
from kubex.k8s.v1_35.apps.v1.deployment import Deployment
from kubex.k8s.v1_35.apps.v1.deployment_spec import DeploymentSpec
from kubex.k8s.v1_35.core.v1.container import Container
from kubex.k8s.v1_35.core.v1.pod_spec import PodSpec
from kubex.k8s.v1_35.core.v1.pod_template_spec import PodTemplateSpec
from kubex.k8s.v1_35.meta.v1.label_selector import LabelSelector
from kubex_core.models.metadata import ObjectMetadata

async def main() -> None:
    client = await create_client()
    async with client:
        api: Api[Deployment] = Api(Deployment, client=client, namespace="default")

        deployment = await api.create(
            Deployment(
                metadata=ObjectMetadata(name="example-deploy", labels={"app": "example"}),
                spec=DeploymentSpec(
                    replicas=1,
                    selector=LabelSelector(match_labels={"app": "example"}),
                    template=PodTemplateSpec(
                        metadata=ObjectMetadata(labels={"app": "example"}),
                        spec=PodSpec(containers=[Container(name="nginx", image="nginx:latest")]),
                    ),
                ),
            ),
        )
        name = cast(str, deployment.metadata.name)

        try:
            # MergePatch — update replicas
            merge_patch = MergePatch(
                Deployment(
                    spec=DeploymentSpec(
                        replicas=3,
                        selector=LabelSelector(match_labels={"app": "example"}),
                        template=PodTemplateSpec(
                            metadata=ObjectMetadata(labels={"app": "example"}),
                            spec=PodSpec(containers=[Container(name="nginx", image="nginx:latest")]),
                        ),
                    )
                )
            )
            patched = await api.patch(name, merge_patch)
            print(f"After MergePatch: replicas={patched.spec and patched.spec.replicas}")

            # StrategicMergePatch — add an annotation
            strategic_patch = StrategicMergePatch(
                Deployment(metadata=ObjectMetadata(annotations={"example.com/patched": "true"}))
            )
            patched = await api.patch(name, strategic_patch)
            print(f"After StrategicMergePatch: annotations={patched.metadata.annotations}")

            # JsonPatch — add a label
            json_patch = JsonPatch().add("/metadata/labels/version", "v1")
            patched = await api.patch(name, json_patch)
            print(f"After JsonPatch: labels={patched.metadata.labels}")
        finally:
            await api.delete(name)
```
