from enum import Enum
from typing import Any, Generic, Type

from pydantic import ValidationError
from kubex_core.models.base_entity import BaseEntity
from kubex_core.models.status import Status
from kubex_core.models.typing import ResourceType

from .exceptions import build_exception


class EventType(str, Enum):
    """EventType is the type of the watch event."""

    ADDED = "ADDED"
    MODIFIED = "MODIFIED"
    DELETED = "DELETED"
    BOOKMARK = "BOOKMARK"
    ERROR = "ERROR"


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
        match self.type:
            case EventType.BOOKMARK:
                self.object = Bookmark.model_validate(raw_event["object"])
            case EventType.ERROR:
                try:
                    status = Status.model_validate(raw_event["object"])
                except ValidationError:
                    raise build_exception(0, str(raw_event["object"]))
                raise build_exception(status.code, status)
            case _:
                self.object = self._resource_type.model_validate(raw_event["object"])

    def __repr__(self) -> str:
        return f"WatchEvent(type={self.type}, object={self.object})"
