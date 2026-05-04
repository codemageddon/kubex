# Metadata

The `metadata` accessor exposes a lightweight API for reading, listing, patching, and watching resource metadata without transferring full resource bodies. This is especially useful when you only need labels, annotations, or `resourceVersion` and want to avoid the bandwidth cost of large spec/status payloads.

Unlike the other subresource accessors, `metadata` is always available on every `Api[T]` instance — no marker interface is required.

## Partial object metadata

All `metadata` operations return `PartialObjectMetadata` instead of the full resource type. `PartialObjectMetadata` contains only:

- `api_version` / `kind`
- `metadata` — the full `ObjectMetadata` (name, namespace, labels, annotations, resourceVersion, uid, ownerReferences, …)

The spec and status fields are absent, which keeps payloads small when you are working at scale.

## Reading a single resource's metadata

```python
from kubex.api import Api
from kubex.client import create_client
from kubex.k8s.v1_35.core.v1.pod import Pod
from kubex_core.models.partial_object_meta import PartialObjectMetadata


async def main() -> None:
    client = await create_client()
    async with client:
        api: Api[Pod] = Api(Pod, client=client, namespace="default")

        meta: PartialObjectMetadata = await api.metadata.get("my-pod")
        print(meta.metadata.resource_version)
        print(meta.metadata.labels)
```

## Listing metadata for all resources

`api.metadata.list()` returns a `ListEntity[PartialObjectMetadata]`. It accepts the same filtering options as `api.list()`:

```python
from kubex_core.models.list_entity import ListEntity
from kubex_core.models.partial_object_meta import PartialObjectMetadata

metas: ListEntity[PartialObjectMetadata] = await api.metadata.list(
    label_selector="app=my-app",
    limit=500,
)
for item in metas.items:
    print(item.metadata.name, item.metadata.resource_version)
```

### List options

| Option | Type | Description |
|--------|------|-------------|
| `label_selector` | `str | None` | Label selector expression |
| `field_selector` | `str | None` | Field selector expression |
| `timeout_seconds` | `int | None` | Server-side `timeoutSeconds` query parameter |
| `limit` | `int | None` | Maximum items per page |
| `continue_token` | `str | None` | Pagination token from a previous response |
| `resource_version` | `str | None` | Minimum resource version for the response |
| `namespace` | `str | None | ...` | Override the `Api` instance namespace |
| `request_timeout` | `Timeout | float | None | ...` | Override the client-level HTTP timeout |

## Patching metadata

Use `api.metadata.patch()` to update labels or annotations without touching the resource spec. All three patch types work:

```python
from kubex.core.patch import MergePatch

updated = await api.metadata.patch(
    "my-pod",
    MergePatch({"metadata": {"labels": {"version": "v2"}}}),
)
print(updated.metadata.labels)
```

`JsonPatch` is also accepted — useful when you want to set or remove a single label without re-sending the full label map:

```python
from kubex.core.patch import JsonPatch, JsonPointer

# Single label, with `/` in the key safely escaped via JsonPointer.
label_path = JsonPointer("/metadata/labels") / "example.com/version"
updated = await api.metadata.patch(
    "my-pod",
    JsonPatch().add(label_path, "v2"),
)
```

For server-side apply, use `ApplyPatch` with `force=True`:

```python
from kubex.core.patch import ApplyPatch

await api.metadata.patch(
    "my-pod",
    ApplyPatch({"metadata": {"labels": {"managed-by": "kubex"}}}),
    force=True,
    field_manager="my-controller",
)
```

### Patch options

| Option | Type | Description |
|--------|------|-------------|
| `dry_run` | `DryRun | bool | None` | Validate without persisting |
| `field_manager` | `str | None` | Field manager name for server-side apply |
| `force` | `bool | None` | Force apply even if fields are owned by another manager |
| `field_validation` | `FieldValidation | None` | Schema validation mode (`Strict`, `Warn`, `Ignore`) |

## Watching metadata changes

`api.metadata.watch()` is an async generator that yields `WatchEvent[PartialObjectMetadata]`:

```python
from kubex_core.models.watch_event import WatchEvent, EventType
from kubex_core.models.partial_object_meta import PartialObjectMetadata

async for event in api.metadata.watch(label_selector="app=my-app"):
    if event.type == EventType.MODIFIED:
        print("modified:", event.object.metadata.name)
```

Watch options mirror those in `api.watch()`. See [Watch](../operations/watch.md) for the restart-on-410-Gone pattern, which applies here too.
