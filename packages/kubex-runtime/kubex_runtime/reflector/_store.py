"""The read side of a cache, and the keys it files objects under."""

from __future__ import annotations

import heapq
import logging
import threading
from collections.abc import Callable
from typing import Generic, TypeVar

from kubex_core.models.base_entity import BaseEntity

from .._waiters import Waiters
from ..object_ref import ObjectRef

logger = logging.getLogger("kubex_runtime.reflector")

K = TypeVar("K", bound=BaseEntity)

_Key = tuple[str | None, str]


def _key(obj: BaseEntity) -> _Key:
    name = obj.metadata.name
    if not name:
        raise ValueError(f"{type(obj).__name__} has no name")
    return obj.metadata.namespace, name


# an object re-created under its name has another uid: it is another object
_ObjectKey = tuple[str | None, str, str | None]


def _object_key(obj: BaseEntity) -> _ObjectKey:
    namespace, name = _key(obj)
    return namespace, name, obj.metadata.uid


def _version_of(value: str | None) -> int | None:
    """`value` as a resourceVersion that compares, None when it does not (an
    aggregated API server's may be opaque)."""
    if value and value.isascii() and value.isdigit():
        return int(value)
    return None


class Store(Generic[K]):
    """The read side of a cache. Its contents only change through its `Writer`;
    `wrote()` records the writes made for an owner, which a controller reading
    the store waits for (see `Controller.running`).

    It can be read from any thread, and waited on in any thread's event loop.

    The objects it returns are the cached ones, shared with every other reader:
    treat them as read-only, and copy one (`obj.model_copy(deep=True)`) before
    changing it.
    """

    def __init__(self) -> None:
        # the writer and the readers may be in different threads
        self._lock = threading.Lock()
        self._objects: dict[_Key, K] = {}
        self._by_namespace: dict[str | None, dict[str, K]] = {}
        self._ready = False
        self._ready_waiters = Waiters(self._lock)
        # the resourceVersion the store is at: every change up to it is in.
        # Raised by each change, set by a re-list to the list's own, or to None
        # for a list without one, which may be another history's
        self._version: int | None = None
        # the newest version written for each owner (by uid) and not seen yet,
        # and as a heap, lowest first: `wrote()` records none the store has
        # seen, and `_advance` drops each as the store reaches it
        self._written: dict[str, int] = {}
        self._written_heap: list[tuple[int, str]] = []
        self._version_waiters = Waiters(self._lock)
        self._warned_opaque = False

    def get(self, ref: ObjectRef) -> K | None:
        """The object `ref` refers to, None if the store does not have it.

        A reference to another kind finds nothing, even when an object of the
        store has its namespace and name.
        """
        with self._lock:
            obj = self._objects.get((ref.namespace, ref.name))
        if obj is None or not ref.is_kind_of(type(obj)):
            return None
        return obj

    def get_named(self, namespace: str | None, name: str) -> K | None:
        """The object `namespace/name`, None if the store does not have it."""
        with self._lock:
            return self._objects.get((namespace, name))

    def state(self) -> list[K]:
        """Every object of the store."""
        with self._lock:
            return list(self._objects.values())

    def namespaced(self, namespace: str | None) -> list[K]:
        """Every object of `namespace`."""
        with self._lock:
            objects = self._by_namespace.get(namespace)
            return [] if objects is None else list(objects.values())

    def find(self, predicate: Callable[[K], bool]) -> list[K]:
        """Every object `predicate` accepts."""
        # outside the lock: `predicate` may take its time, or read the store
        return [obj for obj in self.state() if predicate(obj)]

    def is_ready(self) -> bool:
        """The first list has been applied."""
        return self._ready

    async def wait_until_ready(self) -> None:
        with self._lock:
            if self._ready:
                return
            waiter = self._ready_waiters.add()
        await waiter.wait()

    def wrote(self, obj: K, *, owner: BaseEntity) -> None:
        """Records that `obj`, the response of a create, update or patch this
        process made, was written for `owner`, the object being reconciled. A
        controller that reads this store holds `owner`'s reconciles until the
        store has seen that write.

        Raises `ValueError` when `owner` has no uid. A write whose
        resourceVersion is not an integer is not recorded. Safe from any thread.
        """
        uid = owner.metadata.uid
        if not uid:
            raise ValueError(
                f"{type(owner).__name__} {owner.metadata.name!r} has no uid"
            )
        version = _version_of(obj.metadata.resource_version)
        if version is None:
            self._warn_opaque(obj)
            return
        with self._lock:
            if self._seen(version) or self._written.get(uid, -1) >= version:
                return
            self._written[uid] = version
            heapq.heappush(self._written_heap, (version, uid))

    async def wait_for_writes(self, owner: BaseEntity) -> None:
        """Returns once the store has seen every write recorded for `owner` (a
        controller waits for this itself). Can be awaited in any thread's
        event loop."""
        if uid := owner.metadata.uid:
            await self._wait_for_uid(uid)

    def forget_writes(self) -> None:
        """Drops every write recorded in this store, releasing the objects a
        controller holds for them, and the resourceVersion the store is at: for
        a store that will never see them, such as the cache of a cluster that
        is gone for good, or one whose watch moves to another cluster (call it
        once the old watch has stopped). Writes recorded after it are waited
        for until the store reaches them: its next list, event or bookmark.
        Safe from any thread.
        """
        with self._lock:
            self._written.clear()
            self._written_heap.clear()
            # another cluster's versions do not compare with it
            self._version = None
            self._version_waiters.wake_all()

    def __len__(self) -> int:
        return len(self._objects)

    def __contains__(self, ref: ObjectRef) -> bool:
        return self.get(ref) is not None

    def _pending(self, uid: str) -> bool:
        """A write recorded for the owner `uid` is not in the store yet."""
        with self._lock:
            return uid in self._written

    async def _wait_for_uid(self, uid: str) -> None:
        while True:
            with self._lock:
                if uid not in self._written:
                    return
                waiter = self._version_waiters.add()
            await waiter.wait()

    def _seen(self, version: int) -> bool:
        return self._version is not None and self._version >= version

    def _warn_opaque(self, obj: K) -> None:
        """Warns, once per store, that writes of its kind cannot be waited for."""
        with self._lock:
            if self._warned_opaque:
                return
            self._warned_opaque = True
        logger.warning(
            "%s resourceVersion %r is not an integer: writes of this kind are "
            "not waited for",
            type(obj).__name__,
            obj.metadata.resource_version,
        )

    def _advance(self, version: str | None) -> None:
        """Raises the store's version to `version`, dropping the writes it has
        now seen. Called holding the lock, after the change it came with."""
        parsed = _version_of(version)
        if parsed is None or self._seen(parsed):
            return
        self._version = parsed
        heap = self._written_heap
        while heap and heap[0][0] <= parsed:
            _, uid = heapq.heappop(heap)
            # gone already, or raised by a later write still unseen
            if self._written.get(uid, parsed + 1) <= parsed:
                del self._written[uid]
        self._version_waiters.wake_all()

    def _mark(self, version: str) -> None:
        """The watch has sent every change up to `version` (a bookmark)."""
        with self._lock:
            self._advance(version)

    def _replace(self, objects: dict[_Key, K], version: str | None) -> dict[_Key, K]:
        """Swaps in `objects`, listed at `version`, in one step for readers;
        returns the previous ones."""
        by_namespace: dict[str | None, dict[str, K]] = {}
        for (namespace, name), obj in objects.items():
            by_namespace.setdefault(namespace, {})[name] = obj
        parsed = _version_of(version)
        with self._lock:
            previous = self._objects
            self._objects = objects
            self._by_namespace = by_namespace
            self._ready = True
            # the store holds the list now, so it is at the list's version. The
            # watcher's lists are consistent reads: one below the store comes
            # from another history (another cluster, an etcd restore), whose
            # writes the store will never see
            if (
                parsed is not None
                and self._version is not None
                and parsed < self._version
            ):
                self._written.clear()
                self._written_heap.clear()
            self._version = None
            self._advance(version)
            self._ready_waiters.wake_all()
        return previous

    def _put(self, obj: K) -> None:
        namespace, name = key = _key(obj)
        with self._lock:
            self._objects[key] = obj
            self._by_namespace.setdefault(namespace, {})[name] = obj
            self._advance(obj.metadata.resource_version)

    def _pop(self, obj: K) -> None:
        namespace, name = key = _key(obj)
        with self._lock:
            self._objects.pop(key, None)
            if (objects := self._by_namespace.get(namespace)) is not None:
                objects.pop(name, None)
                if not objects:
                    del self._by_namespace[namespace]
            self._advance(obj.metadata.resource_version)
