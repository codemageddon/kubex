"""``Scheduler``: one entry per key, earliest time wins, debounce restarts.

Bookkeeping tests drive a fake clock: an entry whose time has come on that
clock is returned by ``next()`` without waiting, and one whose time has not come
never is. Only the waiting tests use real (short) delays.
"""

from __future__ import annotations

import anyio
import pytest

from kubex_runtime.scheduler import Scheduler

pytestmark = pytest.mark.anyio


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def _scheduler(debounce: float = 0.0) -> tuple[Scheduler[str, str], FakeClock]:
    clock = FakeClock()
    return Scheduler(debounce=debounce, clock=clock), clock


async def _due(scheduler: Scheduler[str, str]) -> tuple[str, str]:
    """The entry due now; fails if none is."""
    with anyio.fail_after(1):
        return await scheduler.next()


async def _nothing_due(scheduler: Scheduler[str, str]) -> None:
    with anyio.move_on_after(0.05) as scope:
        await scheduler.next()
    assert scope.cancelled_caught, "an entry was returned before its time"


async def test_due_entry_is_returned() -> None:
    scheduler, _ = _scheduler()
    scheduler.schedule("k", "a")
    assert await _due(scheduler) == ("k", "a")
    assert len(scheduler) == 0
    assert "k" not in scheduler


async def test_entry_waits_for_its_delay() -> None:
    scheduler, clock = _scheduler()
    scheduler.schedule("k", "a", delay=10)
    await _nothing_due(scheduler)
    clock.now = 10
    assert await _due(scheduler) == ("k", "a")


async def test_len_and_contains() -> None:
    scheduler, _ = _scheduler()
    assert len(scheduler) == 0
    scheduler.schedule("k", "a", delay=5)
    scheduler.schedule("k", "b", delay=1)
    scheduler.schedule("j", "c", delay=3)
    assert len(scheduler) == 2
    assert "k" in scheduler
    assert "j" in scheduler
    assert "x" not in scheduler


async def test_earlier_request_replaces_later_entry() -> None:
    scheduler, clock = _scheduler()
    scheduler.schedule("k", "late", delay=10)
    scheduler.schedule("k", "early", delay=5)
    assert len(scheduler) == 1
    clock.now = 5
    assert await _due(scheduler) == ("k", "early")
    clock.now = 100
    await _nothing_due(scheduler)


async def test_later_request_keeps_earlier_entry_and_its_payload() -> None:
    scheduler, clock = _scheduler()
    scheduler.schedule("k", "early", delay=5)
    scheduler.schedule("k", "late", delay=10)
    assert len(scheduler) == 1
    clock.now = 5
    assert await _due(scheduler) == ("k", "early")
    clock.now = 100
    await _nothing_due(scheduler)


async def test_superseded_entries_are_dropped() -> None:
    scheduler, clock = _scheduler()
    for delay in (9, 7, 5, 3, 1):
        scheduler.schedule("k", f"after {delay}", delay=delay)
    clock.now = 1
    assert await _due(scheduler) == ("k", "after 1")
    # the four replaced entries are still in the heap: none may come out
    clock.now = 100
    await _nothing_due(scheduler)
    assert len(scheduler) == 0


async def test_entries_come_out_in_time_order() -> None:
    scheduler, clock = _scheduler()
    scheduler.schedule("third", "c", delay=3)
    scheduler.schedule("first", "a", delay=1)
    scheduler.schedule("second", "b", delay=2)
    clock.now = 3
    assert [await _due(scheduler) for _ in range(3)] == [
        ("first", "a"),
        ("second", "b"),
        ("third", "c"),
    ]


async def test_same_time_keeps_scheduling_order() -> None:
    scheduler, _ = _scheduler()
    for key in ("a", "b", "c"):
        scheduler.schedule(key, key)
    assert [(await _due(scheduler))[0] for _ in range(3)] == ["a", "b", "c"]


async def test_debounce_delays_every_entry() -> None:
    scheduler, clock = _scheduler(debounce=2)
    scheduler.schedule("k", "a")
    clock.now = 1.9
    await _nothing_due(scheduler)
    clock.now = 2
    assert await _due(scheduler) == ("k", "a")


async def test_debounce_adds_to_the_delay() -> None:
    scheduler, clock = _scheduler(debounce=2)
    scheduler.schedule("k", "a", delay=3)
    clock.now = 4.9
    await _nothing_due(scheduler)
    clock.now = 5
    assert await _due(scheduler) == ("k", "a")


async def test_trigger_during_debounce_restarts_it() -> None:
    scheduler, clock = _scheduler(debounce=2)
    scheduler.schedule("k", "first")  # due at 2
    clock.now = 1
    scheduler.schedule("k", "second")  # restarts: due at 3
    assert len(scheduler) == 1
    clock.now = 2.5
    await _nothing_due(scheduler)
    clock.now = 3
    assert await _due(scheduler) == ("k", "second")
    clock.now = 100
    await _nothing_due(scheduler)


async def test_burst_of_triggers_runs_once_after_the_last() -> None:
    scheduler, clock = _scheduler(debounce=1)
    for step in range(10):
        clock.now = step * 0.5
        scheduler.schedule("k", f"trigger {step}")
    # last trigger at 4.5: due at 5.5
    clock.now = 5.4
    await _nothing_due(scheduler)
    clock.now = 5.5
    assert await _due(scheduler) == ("k", "trigger 9")
    clock.now = 100
    await _nothing_due(scheduler)


async def test_entry_due_before_the_request_is_kept() -> None:
    scheduler, clock = _scheduler(debounce=2)
    scheduler.schedule("k", "first")  # due at 2
    clock.now = 2.5
    # the first entry was due before this request: it is not pushed back
    scheduler.schedule("k", "second")
    assert await _due(scheduler) == ("k", "first")
    clock.now = 100
    await _nothing_due(scheduler)


async def test_rescheduling_after_taking_out() -> None:
    scheduler, clock = _scheduler()
    scheduler.schedule("k", "a")
    assert await _due(scheduler) == ("k", "a")
    scheduler.schedule("k", "b", delay=1)
    assert "k" in scheduler
    clock.now = 1
    assert await _due(scheduler) == ("k", "b")


async def test_next_waits_for_a_real_delay() -> None:
    scheduler: Scheduler[str, str] = Scheduler()
    with anyio.fail_after(5):
        start = anyio.current_time()
        scheduler.schedule("k", "a", delay=0.1)
        assert await scheduler.next() == ("k", "a")
        assert anyio.current_time() - start >= 0.09


async def test_next_wakes_on_first_schedule() -> None:
    scheduler: Scheduler[str, str] = Scheduler()
    got: list[tuple[str, str]] = []

    async def take() -> None:
        got.append(await scheduler.next())

    with anyio.fail_after(5):
        async with anyio.create_task_group() as group:
            group.start_soon(take)
            await anyio.sleep(0.05)
            assert got == []
            scheduler.schedule("k", "a")
    assert got == [("k", "a")]


async def test_next_wakes_for_an_earlier_entry() -> None:
    scheduler: Scheduler[str, str] = Scheduler()
    scheduler.schedule("late", "a", delay=60)
    got: list[tuple[str, str]] = []

    async def take() -> None:
        got.append(await scheduler.next())

    with anyio.fail_after(5):
        async with anyio.create_task_group() as group:
            group.start_soon(take)
            await anyio.sleep(0.05)
            scheduler.schedule("now", "b")
    assert got == [("now", "b")]
    assert "late" in scheduler


async def test_next_after_cancelled_wait_still_wakes() -> None:
    scheduler: Scheduler[str, str] = Scheduler()
    with anyio.move_on_after(0.02):
        await scheduler.next()
    got: list[tuple[str, str]] = []

    async def take() -> None:
        got.append(await scheduler.next())

    with anyio.fail_after(5):
        async with anyio.create_task_group() as group:
            group.start_soon(take)
            await anyio.sleep(0.05)
            scheduler.schedule("k", "a")
    assert got == [("k", "a")]


def test_schedule_without_a_running_loop() -> None:
    # bookkeeping only needs the clock; the wait event is made by next()
    scheduler, _ = _scheduler()
    scheduler.schedule("k", "a")
    assert "k" in scheduler
