from enum import Enum
from typing import Any, Generic, Type, cast

from .base import BaseEntity, ResourceType


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
            self.object = cast(
                ResourceType, self._resource_type.model_validate(raw_event["object"])
            )