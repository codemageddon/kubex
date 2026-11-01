"""Tasks of any thread's event loop waiting for a change made in any thread.

A store, a writer and its subscriptions may be shared by event loops (asyncio or
trio) running in several threads. An anyio event belongs to one loop, and
`anyio.from_thread` waits for the loop it calls into, so two loops waking each
other would deadlock: a waiter is woken in its own loop, without waiting.
"""

from __future__ import annotations

import asyncio
import sys
import threading
from collections.abc import Callable
from typing import Protocol, TypeVarTuple, Unpack

import anyio

_Ts = TypeVarTuple("_Ts")


class _CallSoon(Protocol):
    """`TrioToken.run_sync_soon` or `AbstractEventLoop.call_soon_threadsafe`."""

    def __call__(
        self, fn: Callable[[Unpack[_Ts]], object], /, *args: Unpack[_Ts]
    ) -> object: ...


def _running_loop() -> tuple[object, _CallSoon] | None:
    """The event loop running here and how to call into it from any thread,
    None outside an event loop."""
    # trio first: in guest mode its tasks run inside a host asyncio loop
    if "trio" in sys.modules:  # not imported, it cannot be running
        import trio

        if trio.lowlevel.in_trio_run():
            token = trio.lowlevel.current_trio_token()
            return token, token.run_sync_soon
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return None
    return loop, loop.call_soon_threadsafe


class Waiters:
    """The tasks waiting for a change of some state that `lock` guards.

    Check the state and `add()` a waiter holding the lock, then wait outside
    it; change the state and `wake_all()` holding it. The tasks may be in any
    thread's event loop, the change in any thread.
    """

    def __init__(self, lock: threading.Lock) -> None:
        self._lock = lock
        # insertion-ordered: woken in the order they came
        self._waiters: dict[Waiter, None] = {}

    def add(self) -> Waiter:
        """A waiter for the next `wake_all()`. Call holding the lock, in an
        event loop."""
        waiter = Waiter(self)
        self._waiters[waiter] = None
        return waiter

    def wake_all(self) -> None:
        """Wakes every waiter. Call holding the lock."""
        if not self._waiters:
            return
        waiters = list(self._waiters)
        self._waiters.clear()
        for waiter in waiters:
            waiter.wake()

    def __len__(self) -> int:
        return len(self._waiters)

    def _discard(self, waiter: Waiter) -> None:
        with self._lock:
            self._waiters.pop(waiter, None)


class Waiter:
    __slots__ = ("_call_soon", "_event", "_loop", "_waiters")

    def __init__(self, waiters: Waiters) -> None:
        running = _running_loop()
        if running is None:
            raise RuntimeError("waiting needs a running event loop")
        self._loop, self._call_soon = running
        self._waiters = waiters
        self._event = anyio.Event()

    async def wait(self) -> None:
        try:
            await self._event.wait()
        finally:
            # woken, it is gone already; cancelled, it is not
            self._waiters._discard(self)

    def wake(self) -> None:
        running = _running_loop()
        if running is not None and running[0] is self._loop:
            self._event.set()
            return
        try:
            self._call_soon(self._event.set)
        except RuntimeError:
            pass  # its loop has ended (trio's RunFinishedError is a RuntimeError)
