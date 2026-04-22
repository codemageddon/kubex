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
    content_type_header: ClassVar[str] = "application/merge-patch+json"

    def __init__(self, body: P) -> None:
        self.body = body

    def serialize(
        self,
        *,
        by_alias: bool = True,
        exclude_unset: bool = True,
        exclude_none: bool = True,
    ) -> str:
        return self.body.model_dump_json(
            by_alias=by_alias, exclude_unset=exclude_unset, exclude_none=exclude_none
        )


class StrategicMergePatch(Patch, Generic[P]):
    content_type_header: ClassVar[str] = "application/strategic-merge-patch+json"

    def __init__(self, body: P) -> None:
        self.body = body

    def serialize(
        self,
        *,
        by_alias: bool = True,
        exclude_unset: bool = True,
        exclude_none: bool = True,
    ) -> str:
        return self.body.model_dump_json(
            by_alias=by_alias, exclude_unset=exclude_unset, exclude_none=exclude_none
        )
