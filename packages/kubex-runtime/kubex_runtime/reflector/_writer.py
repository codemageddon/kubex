"""The write side of a cache, and `reflector()`, which feeds it a watch."""

from __future__ import annotations

import threading
from collections import deque
from collections.abc import AsyncIterable, AsyncIterator
from typing import Generic, TypeVar

from kubex_core.models.base_entity import BaseEntity

from .._closing import closing
from ..watcher import Apply, Bookmark, Delete, Event, Init, InitApply, InitDone
from ._store import Store, _Key, _key, _object_key
from ._subscription import (
    BoundedBuffer,
    MergedBuffer,
    ReflectHandle,
    SubscriberBuffer,
    _BoundedHandle,
    _MergedHandle,
)

K = TypeVar("K", bound=BaseEntity)


class Writer(Generic[K]):
    """The write side of a cache: applies watcher events to its store.

    A re-list is applied atomically: the objects of `Init`..`InitDone` are
    collected aside and replace the store's contents at `InitDone`, so readers
    never see a half-listed store.

    One task applies the events. `subscribe()` works from any thread.
    """

    def __init__(self) -> None:
        self._store: Store[K] = Store()
        self._buffer: dict[_Key, K] | None = None
        # makes a change to the store and the choice of its recipients one step
        # for `subscribe()`, which may be called from another thread
        self._lock = threading.Lock()
        # insertion-ordered set
        self._subscribers: dict[ReflectHandle[K], None] = {}
        # deleted objects and the subscribers that have not got them yet: left
        # by a delivery cancelled while waiting for room, for the next event to
        # finish, as a re-list cannot send them again (the store has dropped them)
        self._owed: deque[tuple[K, deque[ReflectHandle[K]]]] = deque()

    def as_reader(self) -> Store[K]:
        return self._store

    def subscribe(self, buffer: SubscriberBuffer | None = None) -> ReflectHandle[K]:
        """A new subscription, buffered as `buffer` says (a `BoundedBuffer()`
        by default).

        When the store is ready, it starts with every object the store has, so
        a late subscriber misses nothing.
        """
        handle: ReflectHandle[K]
        match buffer:
            case None:
                handle = _BoundedHandle(self, BoundedBuffer().size)
            case BoundedBuffer(size=size):
                handle = _BoundedHandle(self, size)
            case MergedBuffer():
                handle = _MergedHandle(self)
        with self._lock:
            self._subscribers[handle] = None
            if self._store.is_ready():
                handle._prime(self._store.state())
        return handle

    async def apply_watcher_event(self, event: Event[K]) -> None:
        """Applies `event` to the store, then delivers the objects it changed to
        every subscriber, waiting for room in bounded ones; the deletions earlier
        events could not deliver go first.

        Cancelled while waiting, it has applied `event` all the same, and leaves
        the rest undelivered: its deletions are delivered at the next event (a
        later `SharedReflector.run`'s `Init`, say), since a re-list cannot send
        them again; the next re-list sends the other objects again.
        """
        # every branch changes the store, and records the deletions it owes,
        # before it waits
        match event:
            case Init():
                self._buffer = {}
                await self._deliver_owed()
            case InitApply(obj):
                if self._buffer is not None:
                    self._buffer[_key(obj)] = obj
                await self._deliver_owed()
            case InitDone(version):
                listed = self._buffer if self._buffer is not None else {}
                self._buffer = None
                with self._lock:
                    previous = self._store._replace(listed, version)
                    recipients = list(self._subscribers)
                # an object re-created under its name is gone too
                gone = [
                    obj
                    for key, obj in previous.items()
                    if key not in listed or _object_key(listed[key]) != _object_key(obj)
                ]
                earlier = len(self._owed)
                self._owed.extend((obj, deque(recipients)) for obj in gone)
                # the earlier deletions, the listed objects, then the gone ones
                await self._deliver_owed(earlier)
                await self._dispatch(list(listed.values()), recipients)
                await self._deliver_owed()
            case Apply(obj):
                with self._lock:
                    self._store._put(obj)
                    recipients = list(self._subscribers)
                await self._deliver_owed()
                await self._dispatch([obj], recipients)
            case Delete(obj):
                with self._lock:
                    self._store._pop(obj)
                    recipients = list(self._subscribers)
                self._owed.append((obj, deque(recipients)))
                await self._deliver_owed()
            case Bookmark(version):
                self._store._mark(version)
                await self._deliver_owed()

    def _unsubscribe(self, handle: ReflectHandle[K]) -> None:
        with self._lock:
            self._subscribers.pop(handle, None)

    async def _dispatch(
        self, objects: list[K], recipients: list[ReflectHandle[K]]
    ) -> None:
        # the recipients were taken with the change, before a send can wait: a
        # subscriber that joined since was primed with the store, which has it
        for obj in objects:
            for handle in recipients:
                await self._send(handle, obj)

    async def _deliver_owed(self, count: int | None = None) -> None:
        """Delivers the owed deletions, or the first `count` of them."""
        left = len(self._owed) if count is None else count
        while left:
            obj, recipients = self._owed[0]
            while recipients:
                # dropped only once sent: a send cancelled while waiting for room
                # has not queued the object
                await self._send(recipients[0], obj)
                recipients.popleft()
            self._owed.popleft()
            left -= 1

    async def _send(self, handle: ReflectHandle[K], obj: K) -> None:
        if handle not in self._subscribers:
            return  # closed meanwhile
        if not await handle._send(obj):
            self._unsubscribe(handle)


def store() -> tuple[Store[K], Writer[K]]:
    """A new cache: its reader and its writer."""
    writer: Writer[K] = Writer()
    return writer.as_reader(), writer


async def reflector(
    writer: Writer[K], stream: AsyncIterable[Event[K]]
) -> AsyncIterator[Event[K]]:
    """Applies every event of `stream` to `writer`, then passes it on.

    Something has to iterate it for the store to fill: with bounded
    subscriptions, not in the task that reads one of them, which would wait on
    itself once that subscription is full.
    """
    async with closing(stream) as events:
        async for event in events:
            await writer.apply_watcher_event(event)
            yield event
