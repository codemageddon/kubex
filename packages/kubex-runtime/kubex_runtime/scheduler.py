from __future__ import annotations

import heapq
import itertools
from collections.abc import Callable, Hashable
from typing import Generic, TypeVar

import anyio

T = TypeVar("T", bound=Hashable)
P = TypeVar("P")


class Scheduler(Generic[T, P]):
    """A delay queue holding at most one entry per key.

    Scheduling a key that is already scheduled keeps the earlier of the two
    times, with the payload that came with it. Every entry is delayed by
    `debounce`, and a trigger that comes while an entry waits out its debounce
    restarts it, so a burst of triggers for one key runs once, `debounce` after
    the last one (kube-runtime's semantics).

    `clock` must be the clock of the running event loop (the default), since
    `next()` sleeps on it.
    """

    def __init__(
        self,
        *,
        debounce: float = 0.0,
        clock: Callable[[], float] = anyio.current_time,
    ) -> None:
        self._debounce = debounce
        self._clock = clock
        self._scheduled: dict[T, tuple[float, int, P]] = {}
        self._heap: list[tuple[float, int, T]] = []
        self._sequence = itertools.count()
        # created by next(): anyio events cannot be cleared, nor made outside a loop
        self._changed: anyio.Event | None = None

    def schedule(self, key: T, payload: P, delay: float = 0.0) -> None:
        """Runs `key` after `delay` seconds (plus the debounce)."""
        requested = self._clock() + delay
        run_at = requested + self._debounce
        current = self._scheduled.get(key)
        # an entry due before the request was made is kept
        if current is not None and current[0] < requested:
            return
        sequence = next(self._sequence)
        self._scheduled[key] = (run_at, sequence, payload)
        heapq.heappush(self._heap, (run_at, sequence, key))
        if self._changed is not None:
            self._changed.set()

    def __len__(self) -> int:
        return len(self._scheduled)

    def __contains__(self, key: T) -> bool:
        return key in self._scheduled

    async def next(self) -> tuple[T, P]:
        """Waits for the earliest entry to be due and takes it out."""
        while True:
            self._drop_superseded()
            timeout: float | None = None
            if self._heap:
                run_at, _, key = self._heap[0]
                timeout = run_at - self._clock()
                if timeout <= 0:
                    heapq.heappop(self._heap)
                    _, _, payload = self._scheduled.pop(key)
                    return key, payload
            changed = self._changed = anyio.Event()
            with anyio.move_on_after(timeout):
                await changed.wait()

    def _drop_superseded(self) -> None:
        while self._heap:
            _, sequence, key = self._heap[0]
            current = self._scheduled.get(key)
            if current is not None and current[1] == sequence:
                return
            heapq.heappop(self._heap)
