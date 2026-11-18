"""Adapters of watcher streams, and predicates for `predicate_filter`.

Each adapter owns the stream it reads and closes it when it stops.
"""

from __future__ import annotations

from collections.abc import AsyncIterable, AsyncIterator, Callable, Hashable
from typing import TypeVar

from anyio import current_time

from kubex_core.models.base_entity import BaseEntity

from ._closing import closing
from .object_ref import ObjectRef
from .watcher import Apply, Delete, Event, InitApply

K = TypeVar("K", bound=BaseEntity)

Predicate = Callable[[K], Hashable | None]


async def applied_objects(stream: AsyncIterable[Event[K]]) -> AsyncIterator[K]:
    """The objects added or modified, including those of a (re-)list."""
    async with closing(stream) as events:
        async for event in events:
            match event:
                case Apply(obj) | InitApply(obj):
                    yield obj


async def touched_objects(stream: AsyncIterable[Event[K]]) -> AsyncIterator[K]:
    """The objects added, modified or deleted, including those of a (re-)list."""
    async with closing(stream) as events:
        async for event in events:
            match event:
                case Apply(obj) | InitApply(obj) | Delete(obj):
                    yield obj


async def predicate_filter(
    stream: AsyncIterable[K],
    predicate: Predicate[K],
    *,
    ttl: float | None = 3600.0,
) -> AsyncIterator[K]:
    """Drops an object whose `predicate` value did not change since the last one.

    An object for which `predicate` returns None always passes. The value of an
    object not seen for `ttl` seconds is forgotten, so the objects that are gone
    (children with generated names, say) do not pile up; such an object passes
    the next time it comes. None keeps every value.
    """
    # oldest sighting first: a sighting moves an object to the end
    seen: dict[ObjectRef, tuple[Hashable, float]] = {}
    async with closing(stream) as objects:
        async for obj in objects:
            value = predicate(obj)
            if value is None:
                yield obj
                continue
            now = current_time()
            if ttl is not None:
                while seen:
                    oldest = next(iter(seen))
                    if now - seen[oldest][1] < ttl:
                        break
                    del seen[oldest]
            ref = ObjectRef.from_obj(obj)
            previous = seen.pop(ref, None)
            seen[ref] = (value, now)
            if previous is None or previous[0] != value:
                yield obj


def generation(obj: BaseEntity) -> Hashable | None:
    """Changes when the spec does (for kinds with a status subresource).

    Filtering on it skips every change that leaves the generation alone, not
    only status changes: metadata ones too, such as the finalizer `finalizer()`
    adds and then waits to see, and a deletion, which comes with the last state
    of the object. Do not filter a controller's owned or watched objects on it,
    or their deletions trigger nothing; include the finalizers in the value for
    a controller with a finalizer, keeping None (which always passes) for kinds
    without a generation:
    `lambda obj: None if (g := generation(obj)) is None
    else (g, tuple(obj.metadata.finalizers or ()))`.
    """
    gen = obj.metadata.generation
    return None if gen is None else (obj.metadata.uid, gen)


def resource_version(obj: BaseEntity) -> Hashable | None:
    """Changes on every change."""
    return obj.metadata.resource_version
