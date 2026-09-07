from __future__ import annotations

from typing import ClassVar, Generic, Protocol, TypeVar

from pydantic import BaseModel
from yaml import safe_dump

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
    ) -> str:
        return safe_dump(
            self.body.model_dump(
                by_alias=by_alias,
                exclude_unset=exclude_unset,
                exclude_none=exclude_none,
            )
        )


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
