"""Subscriptions to a `Writer`, and the ways they buffer its changes."""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from collections import deque
from collections.abc import AsyncIterator, Iterable
from dataclasses import dataclass
from types import TracebackType
from typing import TYPE_CHECKING, Generic, TypeAlias, TypeVar

import anyio.lowlevel

from kubex_core.models.base_entity import BaseEntity

from .._waiters import Waiters
from ._store import _object_key, _ObjectKey

if TYPE_CHECKING:
    from ._writer import Writer

K = TypeVar("K", bound=BaseEntity)


@dataclass(frozen=True)
class BoundedBuffer:
    """Every change, in order, through a queue of at most `size` objects.

    When the queue is full the writer waits for the subscriber to read, so a
    subscriber that falls behind holds up the watch, and the store, for every
    other reader too.
    """

    size: int = 1024

    def __post_init__(self) -> None:
        if self.size < 1:
            raise ValueError("size must be at least 1")


@dataclass(frozen=True)
class MergedBuffer:
    """The latest state of every changed object, one entry per object.

    A change to an object that is already waiting replaces it in place, so the
    subscriber skips the states in between and the writer never waits. An object
    deleted and re-created under its name is two objects (their uids differ):
    the deletion still comes, apart from the new object (after it, when a re-list
    finds the change). So the buffer holds at most
    the objects of the store and those deleted since the subscriber last read.
    Suits subscribers that read the latest state anyway, as controllers do.
    """


SubscriberBuffer: TypeAlias = BoundedBuffer | MergedBuffer


class ReflectHandle(ABC, Generic[K]):
    """A subscription to a `Writer`: every object it applied, after applying it.

    A deleted object comes with its last state and is no longer in the store when
    it arrives; a re-list sends every object it found, and the last state of
    every object it no longer found (one re-created under its name since, with
    another uid, included).

    Close a subscription you stop reading (`aclose()`, or `async with`): the
    writer keeps sending to an open one. A controller closes the stream it is
    given when it stops.

    It can be read in another thread's event loop than the writer's, and closed
    from any thread.
    """

    def __init__(self, writer: Writer[K]) -> None:
        self._writer = writer
        # guards the buffer and `_closed`: the writer and the reader may be in
        # different threads
        self._lock = threading.Lock()
        self._closed = False
        self._readers = Waiters(self._lock)

    def __aiter__(self) -> AsyncIterator[K]:
        return self

    @abstractmethod
    async def __anext__(self) -> K: ...

    def close(self) -> None:
        """Unsubscribes, dropping what is buffered: iterating ends."""
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._drop()
        self._writer._unsubscribe(self)

    async def aclose(self) -> None:
        self.close()

    async def __aenter__(self) -> ReflectHandle[K]:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    @abstractmethod
    def _drop(self) -> None:
        """Empties the buffer and wakes every task waiting on it: the
        subscription is closed. Called holding the lock."""

    @abstractmethod
    def _prime(self, objects: Iterable[K]) -> None:
        """Queues the store's contents for a late subscriber, without waiting."""

    @abstractmethod
    async def _send(self, obj: K) -> bool:
        """Delivers `obj`; False when the subscription is closed."""


class _BoundedHandle(ReflectHandle[K]):
    def __init__(self, writer: Writer[K], size: int) -> None:
        super().__init__(writer)
        self._size = size
        self._queue: deque[K] = deque()
        # the store snapshot of a late subscriber, read before the queue and
        # not counted in its size
        self._replay: deque[K] = deque()
        self._writers = Waiters(self._lock)

    async def __anext__(self) -> K:
        with self._lock:
            if self._replay:
                return self._replay.popleft()
        await anyio.lowlevel.checkpoint()
        while True:
            with self._lock:
                if self._queue:
                    obj = self._queue.popleft()
                    self._writers.wake_all()
                    return obj
                if self._closed:
                    raise StopAsyncIteration
                reader = self._readers.add()
            await reader.wait()

    def _drop(self) -> None:
        self._replay.clear()
        self._queue.clear()
        self._readers.wake_all()
        # a writer waiting for room finds it closed, and drops it
        self._writers.wake_all()

    def _prime(self, objects: Iterable[K]) -> None:
        with self._lock:
            self._replay.extend(objects)

    async def _send(self, obj: K) -> bool:
        await anyio.lowlevel.checkpoint()
        while True:
            with self._lock:
                if self._closed:
                    return False
                if len(self._queue) < self._size:
                    self._queue.append(obj)
                    self._readers.wake_all()
                    return True
                writer = self._writers.add()
            await writer.wait()


class _MergedHandle(ReflectHandle[K]):
    def __init__(self, writer: Writer[K]) -> None:
        super().__init__(writer)
        # insertion-ordered: an update keeps the object's place in line
        self._pending: dict[_ObjectKey, K] = {}

    async def __anext__(self) -> K:
        while True:
            with self._lock:
                if self._pending:
                    key = next(iter(self._pending))
                    return self._pending.pop(key)
                if self._closed:
                    raise StopAsyncIteration
                reader = self._readers.add()
            await reader.wait()

    def _drop(self) -> None:
        self._pending.clear()
        self._readers.wake_all()

    def _prime(self, objects: Iterable[K]) -> None:
        with self._lock:
            for obj in objects:
                self._pending[_object_key(obj)] = obj
            self._readers.wake_all()

    async def _send(self, obj: K) -> bool:
        key = _object_key(obj)
        with self._lock:
            if self._closed:
                return False
            self._pending[key] = obj
            self._readers.wake_all()
        return True
