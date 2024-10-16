from enum import Enum
from typing import Any, ClassVar, Generic

from kubex.models.base import ResourceType


class PatchTypes(str, Enum):
    APPLY_PATCH = "ApplyPatch"
    JSON_PATCH = "JsonPatch"
    MERGE_PATCH = "MergePatch"
    STRATEGIC_MERGE_PATCH = "StrategicMergePatch"


PATCH_HEADERS = {
    PatchTypes.APPLY_PATCH: "application/apply-patch+yaml",
    PatchTypes.JSON_PATCH: "application/json-patch+json",
    PatchTypes.MERGE_PATCH: "application/merge-patch+json",
    PatchTypes.STRATEGIC_MERGE_PATCH: "application/strategic-merge-patch+json",
}


class ApplyPatch(Generic[ResourceType]):
    content_type_header: ClassVar[str] = "application/apply-patch+yaml"

    def __init__(self, body: ResourceType) -> None:
        self.body = body


class MergePatch(Generic[ResourceType]):
    content_type_header: ClassVar[str] = "application/merge-patch+json"

    def __init__(self, body: ResourceType) -> None:
        self.body = body


class StrategicMergePatch(Generic[ResourceType]):
    content_type_header: ClassVar[str] = "application/strategic-merge-patch+json"

    def __init__(self, body: ResourceType) -> None:
        self.body = body


class JsonPatch:
    content_type_header: ClassVar[str] = "application/json-patch+json"

    def __init__(self, body: list[dict[str, Any]]) -> None:
        self.body = body
