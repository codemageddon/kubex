from enum import Enum
from typing import Any, Generic, Type

from .base_entity import BaseEntity
from .typing import ResourceType


class EventType(str, Enum):
    """EventType is the type of the watch event."""

    ADDED = "ADDED"
    MODIFIED = "MODIFIED"
    DELETED = "DELETED"
    BOOKMARK = "BOOKMARK"


class Bookmark(BaseEntity):
    """Bookmark is a pointer to a resource in a stream."""


class WatchEvent(Generic[ResourceType]):
    """WatchEvent represents a single event from a watch stream."""

    def __init__(
        self, resource_type: Type[ResourceType], raw_event: dict[str, Any]
    ) -> None:
        self._resource_type = resource_type
        self.type = EventType(raw_event["type"])
        self.object: ResourceType | Bookmark
        if self.type == EventType.BOOKMARK:
            self.object = Bookmark.model_validate(raw_event["object"])
        else:
            self.object = self._resource_type.model_validate(raw_event["object"])

    def __repr__(self) -> str:
        return f"WatchEvent(type={self.type}, object={self.object})"
