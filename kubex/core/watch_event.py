from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Generic, Type

from pydantic import ValidationError
from kubex_core.models.base_entity import BaseEntity
from kubex_core.models.status import Status
from kubex_core.models.typing import ResourceType

from .exceptions import build_exception
from .invalid_object import InvalidObject, _invalid_object_or_raise
from .params import InvalidObjects

INITIAL_EVENTS_END_ANNOTATION = "k8s.io/initial-events-end"
"""Annotation on the bookmark that ends the initial events of a watch started
with ``send_initial_events=True``."""


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

    @property
    def is_initial_events_end(self) -> bool:
        """Whether this is the bookmark that ends the initial events.

        A watch started with ``send_initial_events=True`` first sends an ``ADDED``
        event for every existing object, then this bookmark. From here on the
        stream carries live changes, and the bookmark's
        ``object.metadata.resource_version`` is the first one a watch can resume
        from. Other bookmarks are periodic checkpoints and return ``False``.
        """
        if self.type is not EventType.BOOKMARK or not isinstance(self.object, Bookmark):
            return False
        annotations = self.object.metadata.annotations or {}
        return annotations.get(INITIAL_EVENTS_END_ANNOTATION) == "true"

    def __repr__(self) -> str:
        return f"WatchEvent(type={self.type}, object={self.object})"


@dataclass(frozen=True, eq=False)
class InvalidWatchEvent:
    """A watch event whose object does not fit the resource model.

    Yielded by ``Api.watch(invalid=InvalidObjects.INCLUDE)`` in place of a
    ``WatchEvent`` for an ``ADDED``, ``MODIFIED`` or ``DELETED`` event; the stream
    goes on. Like a ``WatchEvent`` it has ``type`` and ``object.metadata``, so code
    that only needs an object's name, namespace or resource version works on both.

    Attributes:
        type: ``ADDED``, ``MODIFIED`` or ``DELETED``.
        object: The object, with its raw data, the validation error and its
            metadata.
    """

    type: EventType
    object: InvalidObject

    @property
    def is_initial_events_end(self) -> bool:
        """Always ``False``: only a bookmark ends the initial events."""
        return False


def _parse_watch_event(
    resource_type: Type[ResourceType],
    raw_event: dict[str, Any],
    invalid: InvalidObjects,
) -> WatchEvent[ResourceType] | InvalidWatchEvent:
    """Parse one decoded watch line.

    With ``InvalidObjects.INCLUDE``, an ``ADDED``/``MODIFIED``/``DELETED`` object
    that does not fit ``resource_type`` becomes an ``InvalidWatchEvent``. Nothing
    else is tolerated: an ``ERROR`` event raises its API error, and a bookmark
    that does not parse raises, as both mean the stream itself is wrong.
    """
    try:
        return WatchEvent(resource_type, raw_event)
    except ValidationError as error:
        event_type = EventType(raw_event["type"])
        if invalid is InvalidObjects.RAISE or event_type is EventType.BOOKMARK:
            raise
        return InvalidWatchEvent(
            event_type, _invalid_object_or_raise(raw_event["object"], error)
        )
