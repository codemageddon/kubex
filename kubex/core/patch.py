from __future__ import annotations

import json
from typing import Any, ClassVar, Generic, Protocol, TypeVar

from pydantic import BaseModel

from kubex.core.json_patch import (
    JsonPatch,
    JsonPatchAdd,
    JsonPatchCopy,
    JsonPatchMove,
    JsonPatchOperation,
    JsonPatchRemove,
    JsonPatchReplace,
    JsonPatchTest,
)
from kubex.core.json_pointer import JsonPointer

__all__ = [
    "ApplyPatch",
    "JsonPatch",
    "JsonPatchAdd",
    "JsonPatchCopy",
    "JsonPatchMove",
    "JsonPatchOperation",
    "JsonPatchRemove",
    "JsonPatchReplace",
    "JsonPatchTest",
    "JsonPointer",
    "MergePatch",
    "Patch",
    "StrategicMergePatch",
]

P = TypeVar("P", bound=BaseModel)


class Patch(Protocol):
    content_type_header: ClassVar[str]

    def serialize(
        self,
        *,
        by_alias: bool = True,
        exclude_unset: bool = True,
        exclude_none: bool = True,
    ) -> str | bytes: ...


class ApplyPatch(Patch, Generic[P]):
    """Server-side apply patch (`application/apply-patch+yaml`).

    The body is serialized as JSON (valid YAML, and what `kubectl apply
    --server-side` sends), so timestamps and other non-primitive fields use
    their JSON wire format.

    `apiVersion` and `kind` are always sent, even though `exclude_unset` would
    drop them when they are only model defaults: the server rejects an apply
    patch without them. Request builders pass the target resource's values
    explicitly (so e.g. a `PartialObjectMetadata` body applied through
    `api.metadata.patch()` is sent as the target kind); otherwise they come
    from the body, falling back to its `__RESOURCE_CONFIG__`.
    `metadata.managedFields` is always dropped since the server rejects any
    non-nil value. `metadata.resourceVersion` is kept and acts as an
    optimistic-concurrency precondition, so when applying an object fetched
    earlier, clear it (`obj.metadata.resource_version = None`) unless a
    `Conflict` on concurrent changes is what you want.

    Unlike `MergePatch`/`StrategicMergePatch`, `exclude_none` defaults to `True`
    here: a field management conflict is reported by field ownership, not by
    an explicit `null`, so there is no RFC 7396-style "null deletes the field"
    convention to preserve.
    """

    content_type_header: ClassVar[str] = "application/apply-patch+yaml"

    def __init__(self, body: P) -> None:
        self.body = body

    def serialize(
        self,
        *,
        by_alias: bool = True,
        exclude_unset: bool = True,
        exclude_none: bool = True,
        api_version: str | None = None,
        kind: str | None = None,
    ) -> str:
        data: dict[str, Any] = self.body.model_dump(
            mode="json",
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_none=exclude_none,
        )
        api_version_key = "apiVersion" if by_alias else "api_version"
        head: dict[str, Any] = {}
        for key, field, override in (
            (api_version_key, "api_version", api_version),
            ("kind", "kind", kind),
        ):
            from_body = data.pop(key, None)
            value = override or from_body or _type_field(self.body, field)
            if value:
                head[key] = value
        metadata = data.get("metadata")
        if isinstance(metadata, dict):
            metadata.pop("managedFields" if by_alias else "managed_fields", None)
        return json.dumps({**head, **data}, ensure_ascii=False)


def _type_field(body: BaseModel, field: str) -> str | None:
    """`api_version`/`kind` of `body`: the model value (set or defaulted),
    else its resource config's, else `None`."""
    value = getattr(body, field, None)
    if isinstance(value, str) and value:
        return value
    config = getattr(type(body), "__RESOURCE_CONFIG__", None)
    if config is None:
        return None
    try:
        resolved = getattr(config, field)
    except ValueError:  # config not fully populated
        return None
    return resolved if isinstance(resolved, str) and resolved else None


class MergePatch(Patch, Generic[P]):
    """RFC 7396 JSON merge patch (`application/merge-patch+json`).

    `exclude_none` defaults to `False`: RFC 7396 uses an explicit `null` to
    delete a key, so a field the caller deliberately set to `None` must reach
    the server as `null` rather than being stripped before serialization.
    `exclude_unset` still limits the patch to fields the caller actually
    touched, so fields left at their default remain distinguishable from
    explicitly null ones.
    """

    content_type_header: ClassVar[str] = "application/merge-patch+json"

    def __init__(self, body: P) -> None:
        self.body = body

    def serialize(
        self,
        *,
        by_alias: bool = True,
        exclude_unset: bool = True,
        exclude_none: bool = False,
    ) -> str:
        return self.body.model_dump_json(
            by_alias=by_alias, exclude_unset=exclude_unset, exclude_none=exclude_none
        )


class StrategicMergePatch(Patch, Generic[P]):
    """Kubernetes strategic merge patch (`application/strategic-merge-patch+json`).

    `exclude_none` defaults to `False` for the same reason as `MergePatch`: an
    explicit `null` is meaningful (it deletes the field) and must not be
    stripped before serialization.
    """

    content_type_header: ClassVar[str] = "application/strategic-merge-patch+json"

    def __init__(self, body: P) -> None:
        self.body = body

    def serialize(
        self,
        *,
        by_alias: bool = True,
        exclude_unset: bool = True,
        exclude_none: bool = False,
    ) -> str:
        return self.body.model_dump_json(
            by_alias=by_alias, exclude_unset=exclude_unset, exclude_none=exclude_none
        )
