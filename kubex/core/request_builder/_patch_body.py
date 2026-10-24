from __future__ import annotations

import json
from typing import Any

from kubex.core.patch import ApplyPatch, MergePatch, Patch, StrategicMergePatch
from kubex_core.models.resource_config import ResourceConfig


def patch_body(
    patch: Patch,
    target: ResourceConfig[Any] | None = None,
    *,
    drop_merge_type_fields: bool = False,
) -> str | bytes:
    """Serialize `patch` for a PATCH request.

    With `target`, a server-side apply body is stamped with the target
    resource's `apiVersion`/`kind`, which the apiserver requires to match the
    endpoint (e.g. a `PartialObjectMetadata` body sent to a Pod's metadata).

    With `drop_merge_type_fields`, `apiVersion`/`kind` are removed from merge
    and strategic-merge bodies: a body built from a fetched
    `PartialObjectMetadata` carries its own type, which the apiserver rejects
    when merged into the target object.
    """
    if target is not None and isinstance(patch, ApplyPatch):
        return patch.serialize(api_version=target.api_version, kind=target.kind)
    serialized = patch.serialize()
    if drop_merge_type_fields and isinstance(patch, (MergePatch, StrategicMergePatch)):
        data = json.loads(serialized)
        if isinstance(data, dict):
            data.pop("apiVersion", None)
            data.pop("kind", None)
            return json.dumps(data, ensure_ascii=False)
    return serialized
