"""The reconcile requests a controller's triggers make of the streams they read."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterable, AsyncIterator
from typing import Any, TypeVar

from kubex_core.models.base_entity import BaseEntity

from .._closing import closing
from ..object_ref import ObjectRef
from ..reflector import MergedBuffer, SharedReflector, Store, SubscriberBuffer
from ..watcher import Apply, Delete, Event, Init, InitApply, InitDone
from ._types import (
    BULK_RECONCILE,
    OBJECT_UPDATED,
    UNKNOWN,
    Adapter,
    Mapper,
    ReconcileReason,
    ReconcileRequest,
)

logger = logging.getLogger("kubex_runtime.controller")

K = TypeVar("K", bound=BaseEntity)
R = TypeVar("R", bound=BaseEntity)


async def _self_triggers(
    stream: AsyncIterable[K],
) -> AsyncIterator[ReconcileRequest]:
    async with closing(stream) as objects:
        async for obj in objects:
            yield ReconcileRequest(ObjectRef.from_obj(obj), OBJECT_UPDATED)


async def _mapped_triggers(
    stream: AsyncIterable[R], mapper: Mapper[R]
) -> AsyncIterator[ReconcileRequest]:
    async with closing(stream) as objects:
        async for obj in objects:
            for request in _mapped(obj, mapper):
                yield request


async def _watched_triggers(
    stream: AsyncIterable[Event[R]], mapper: Mapper[R]
) -> AsyncIterator[ReconcileRequest]:
    """`_mapped_triggers` of a watcher's objects, plus the triggers of every
    object a re-list no longer finds: deleted while the watch was down, it
    sends no `Delete`.
    """
    # what each object mapped to, not the object: no second cache of the
    # kind. Keyed with the uid, so an object re-created under its name while
    # the watch was down is gone too
    known: dict[_Seen, list[ReconcileRequest]] = {}
    listed: dict[_Seen, list[ReconcileRequest]] | None = None
    async with closing(stream) as events:
        async for event in events:
            match event:
                case Init():
                    # a list that started over has triggered for what it
                    # found: the next one may no longer find it
                    if listed:
                        known.update(listed)
                    listed = {}
                case InitApply(obj):
                    requests = _mapped(obj, mapper)
                    if listed is not None and requests:
                        listed[_seen(obj)] = requests
                    for request in requests:
                        yield request
                case InitDone():
                    relisted = listed if listed is not None else {}
                    listed = None
                    gone = [
                        requests
                        for key, requests in known.items()
                        if key not in relisted
                    ]
                    known = relisted
                    for requests in gone:
                        for request in requests:
                            yield request
                case Apply(obj):
                    requests = _mapped(obj, mapper)
                    if requests:
                        known[_seen(obj)] = requests
                    else:
                        known.pop(_seen(obj), None)
                    for request in requests:
                        yield request
                case Delete(obj):
                    known.pop(_seen(obj), None)
                    for request in _mapped(obj, mapper):
                        yield request


async def _ref_triggers(
    stream: AsyncIterable[ObjectRef],
) -> AsyncIterator[ReconcileRequest]:
    async with closing(stream) as refs:
        async for ref in refs:
            yield ReconcileRequest(ref, UNKNOWN)


async def _bulk_triggers(
    stream: AsyncIterable[Any], store: Store[K]
) -> AsyncIterator[ReconcileRequest]:
    async with closing(stream) as signals:
        async for _ in signals:
            for obj in store.state():
                yield ReconcileRequest(ObjectRef.from_obj(obj), BULK_RECONCILE)


def _mapped(obj: R, mapper: Mapper[R]) -> list[ReconcileRequest]:
    """The triggers `mapper` makes of `obj`; none, logged, when it fails."""
    try:
        refs = list(mapper(obj))
    except Exception:
        logger.exception(
            "mapper failed for %s/%s", obj.metadata.namespace, obj.metadata.name
        )
        return []
    reason = ReconcileReason.related_object_updated(ObjectRef.from_obj(obj))
    return [ReconcileRequest(ref, reason) for ref in refs]


# an object of a watch: its reference and uid
_Seen = tuple[ObjectRef, str | None]


def _seen(obj: BaseEntity) -> _Seen:
    return ObjectRef.from_obj(obj), obj.metadata.uid


async def _subscription(
    shared: SharedReflector[R],
    buffer: SubscriberBuffer | None,
    adapt: Adapter[R] | None,
) -> AsyncIterator[R]:
    """A subscription to `shared`, made once iterated and closed when done,
    whether or not `adapt` closes the stream it wraps.
    """
    handle = shared.subscribe(MergedBuffer() if buffer is None else buffer)
    try:
        stream: AsyncIterable[R] = handle if adapt is None else adapt(handle)
        async with closing(stream) as objects:
            async for obj in objects:
                yield obj
    finally:
        handle.close()
