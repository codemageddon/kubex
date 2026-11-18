"""kubex-runtime across threads: stores read from any thread, readiness and
subscriptions waited on in other event loops than the writer's, and runs and
backoffs used from several threads at once. The free-threaded build runs the
threads in parallel."""

from __future__ import annotations

import contextvars
import threading
from collections.abc import Awaitable, Callable
from typing import Generic, TypeVar, cast

import anyio
import anyio.to_thread
import pytest

from kubex.k8s.v1_35.core.v1.config_map import ConfigMap
from kubex_runtime import (
    Action,
    Apply,
    BoundedBuffer,
    Controller,
    Delete,
    ExponentialBackoff,
    Init,
    InitApply,
    InitDone,
    MergedBuffer,
    ObjectRef,
    SharedReflector,
    SubscriberBuffer,
    Writer,
)
from kubex_runtime._waiters import Waiters
from test.test_runtime._fakes import FakeApi, Page, cm

pytestmark = pytest.mark.anyio

_TIMEOUT = 5
_THREADS = 8

T = TypeVar("T")

# the event loop of the other thread, whatever the test's own
OTHER_LOOPS = pytest.mark.parametrize("other", ["asyncio", "trio"])
BUFFERS = pytest.mark.parametrize(
    "buffer", [BoundedBuffer(size=1), MergedBuffer()], ids=["bounded", "merged"]
)


def _run_loop(func: Callable[[], Awaitable[T]], backend: str) -> T:
    # in an empty context: a thread started by a task may inherit its context
    # (the default of free-threaded 3.14), where anyio sees that task's loop
    return contextvars.Context().run(lambda: anyio.run(func, backend=backend))


class _LoopThread(Generic[T]):
    """Runs `func` in a new thread, in an event loop of its own."""

    def __init__(self, func: Callable[[], Awaitable[T]], backend: str) -> None:
        self._result: T | None = None
        self._error: BaseException | None = None
        self._thread = threading.Thread(
            target=self._run, args=(func, backend), daemon=True
        )
        self._thread.start()

    def _run(self, func: Callable[[], Awaitable[T]], backend: str) -> None:
        try:
            self._result = _run_loop(func, backend)
        except BaseException as error:
            self._error = error

    async def result(self) -> T:
        await anyio.to_thread.run_sync(self._thread.join, _TIMEOUT)
        assert not self._thread.is_alive(), "the other loop did not finish"
        if self._error is not None:
            raise self._error
        return cast(T, self._result)


class _Threads:
    """Runs `target` in several threads until stopped, keeping what they raise."""

    def __init__(self, target: Callable[[], None], count: int = 4) -> None:
        self.errors: list[BaseException] = []
        self._stop = threading.Event()
        self._target = target
        self._threads = [
            threading.Thread(target=self._run, daemon=True) for _ in range(count)
        ]
        for thread in self._threads:
            thread.start()

    def _run(self) -> None:
        try:
            while not self._stop.is_set():
                self._target()
        except BaseException as error:
            self.errors.append(error)

    async def stop(self) -> None:
        self._stop.set()
        for thread in self._threads:
            await anyio.to_thread.run_sync(thread.join, _TIMEOUT)
            assert not thread.is_alive()


def _race(attempt: Callable[[], Awaitable[None]]) -> list[BaseException | None]:
    """Runs `attempt` in several threads at once, each in an asyncio loop of its
    own: what each raised."""
    barrier = threading.Barrier(_THREADS)
    outcomes: list[BaseException | None] = []
    lock = threading.Lock()

    def run() -> None:
        barrier.wait()
        outcome: BaseException | None = None
        try:
            _run_loop(attempt, "asyncio")
        except BaseException as error:
            outcome = error
        with lock:
            outcomes.append(outcome)

    threads = [threading.Thread(target=run, daemon=True) for _ in range(_THREADS)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(_TIMEOUT)
    assert len(outcomes) == _THREADS
    return outcomes


async def _until(condition: Callable[[], bool]) -> None:
    with anyio.fail_after(_TIMEOUT):
        while not condition():
            await anyio.sleep(0.001)


async def _list(writer: Writer[ConfigMap], *objects: ConfigMap) -> None:
    await writer.apply_watcher_event(Init())
    for obj in objects:
        await writer.apply_watcher_event(InitApply(obj))
    await writer.apply_watcher_event(InitDone())


async def _reconcile(obj: ConfigMap, ctx: None) -> Action:
    return Action.await_change()


def _error_policy(obj: ConfigMap, error: Exception, ctx: None) -> Action:
    return Action.await_change()


# -- the store --------------------------------------------------------------------


async def test_readers_in_other_threads_see_whole_relists() -> None:
    writer: Writer[ConfigMap] = Writer()
    store = writer.as_reader()
    lists = {
        "a": [cm(f"a{i}") for i in range(200)],
        "b": [cm(f"b{i}") for i in range(100)],
    }
    problems: list[str] = []

    def read() -> None:
        for objects in (store.state(), store.namespaced("ns")):
            prefixes = {str(obj.metadata.name)[0] for obj in objects}
            if objects and (
                len(prefixes) != 1 or len(objects) != len(lists[prefixes.pop()])
            ):
                problems.append(f"{len(objects)} objects of lists {prefixes}")

    readers = _Threads(read)
    try:
        for _ in range(50):
            for objects in lists.values():
                await _list(writer, *objects)
    finally:
        await readers.stop()
    assert readers.errors == []
    assert problems == []


async def test_readers_in_other_threads_during_changes() -> None:
    writer: Writer[ConfigMap] = Writer()
    store = writer.as_reader()
    objects = [cm(f"o{i}", namespace=f"ns{i % 3}") for i in range(300)]
    ref = ObjectRef.of(ConfigMap, "o1", "ns1")
    await _list(writer)

    def read() -> None:
        store.find(lambda obj: obj.metadata.namespace == "ns0")
        store.namespaced("ns1")
        store.state()
        store.get(ref)
        store.get_named("ns1", "o1")
        assert len(store) >= 0
        assert isinstance(ref in store, bool)

    readers = _Threads(read)
    try:
        for _ in range(20):
            for obj in objects:
                await writer.apply_watcher_event(Apply(obj))
            for obj in objects:
                await writer.apply_watcher_event(Delete(obj))
    finally:
        await readers.stop()
    assert readers.errors == []


async def test_a_find_predicate_may_read_the_store() -> None:
    writer: Writer[ConfigMap] = Writer()
    store = writer.as_reader()
    await _list(writer, cm("a"), cm("b"))
    found = store.find(lambda obj: store.get_named("ns", "a") is obj)
    assert [obj.metadata.name for obj in found] == ["a"]


@OTHER_LOOPS
async def test_wait_until_ready_in_another_loop(other: str) -> None:
    writer: Writer[ConfigMap] = Writer()
    store = writer.as_reader()
    waiting = _LoopThread(store.wait_until_ready, other)
    await _until(lambda: len(store._ready_waiters) == 1)
    await _list(writer, cm("a"))
    await waiting.result()


@OTHER_LOOPS
async def test_a_write_recorded_and_waited_for_in_another_loop(other: str) -> None:
    writer: Writer[ConfigMap] = Writer()
    store = writer.as_reader()
    parent = cm("parent", uid="uid-parent")

    async def record_and_wait() -> None:
        store.wrote(cm("child", "10"), owner=parent)
        await store.wait_for_writes(parent)

    waiting = _LoopThread(record_and_wait, other)
    await _until(lambda: len(store._version_waiters) == 1)
    await writer.apply_watcher_event(Apply(cm("child", "10")))
    await waiting.result()


async def test_forget_writes_from_another_thread_releases_a_waiting_task() -> None:
    store = Writer[ConfigMap]().as_reader()
    parent = cm("parent", uid="uid-parent")
    store.wrote(cm("child", "10"), owner=parent)
    with anyio.fail_after(_TIMEOUT):
        async with anyio.create_task_group() as group:
            group.start_soon(store.wait_for_writes, parent)
            await _until(lambda: len(store._version_waiters) == 1)
            await anyio.to_thread.run_sync(store.forget_writes)


# -- subscriptions ----------------------------------------------------------------


@OTHER_LOOPS
@BUFFERS
async def test_subscription_read_in_another_loop(
    buffer: SubscriberBuffer, other: str
) -> None:
    writer: Writer[ConfigMap] = Writer()
    handle = writer.subscribe(buffer)
    names = [f"o{i}" for i in range(200)]

    async def read() -> list[str]:
        with anyio.fail_after(_TIMEOUT):
            return [str((await handle.__anext__()).metadata.name) for _ in names]

    reading = _LoopThread(read, other)
    # a one-object queue: the writer waits for the other loop to read, which
    # wakes it
    with anyio.fail_after(_TIMEOUT):
        await _list(writer)
        for name in names:
            await writer.apply_watcher_event(Apply(cm(name)))
    assert await reading.result() == names


@OTHER_LOOPS
@BUFFERS
async def test_closing_ends_a_reader_in_another_loop(
    buffer: SubscriberBuffer, other: str
) -> None:
    writer: Writer[ConfigMap] = Writer()
    handle = writer.subscribe(buffer)

    async def read() -> list[ConfigMap]:
        with anyio.fail_after(_TIMEOUT):
            return [obj async for obj in handle]

    reading = _LoopThread(read, other)
    await _until(lambda: len(handle._readers) == 1)
    handle.close()
    assert await reading.result() == []


async def test_closing_in_another_thread_frees_a_waiting_writer() -> None:
    writer: Writer[ConfigMap] = Writer()
    handle = writer.subscribe(BoundedBuffer(size=1))
    with anyio.fail_after(_TIMEOUT):
        await _list(writer)
        await writer.apply_watcher_event(Apply(cm("a")))  # fills the queue
        async with anyio.create_task_group() as group:
            group.start_soon(writer.apply_watcher_event, Apply(cm("b")))
            await anyio.sleep(0.05)  # the writer waits for room
            await anyio.to_thread.run_sync(handle.close)
        # dropped: no more waiting
        await writer.apply_watcher_event(Apply(cm("c")))


async def test_subscribing_and_closing_in_other_threads_during_changes() -> None:
    writer: Writer[ConfigMap] = Writer()
    await _list(writer, cm("a"))

    def churn() -> None:
        for buffer in (BoundedBuffer(), MergedBuffer()):
            writer.subscribe(buffer).close()

    churners = _Threads(churn)
    try:
        with anyio.fail_after(_TIMEOUT):
            for i in range(3000):
                await writer.apply_watcher_event(Apply(cm(f"o{i % 50}")))
    finally:
        await churners.stop()
    assert churners.errors == []
    assert writer._subscribers == {}


@OTHER_LOOPS
async def test_waking_a_waiter_whose_loop_ended(other: str) -> None:
    lock = threading.Lock()
    waiters = Waiters(lock)

    async def add() -> None:
        with lock:
            waiters.add()

    await _LoopThread(add, other).result()
    with lock:
        waiters.wake_all()  # nothing waits any more: nothing to do, nothing raised


# -- controllers and shared reflectors --------------------------------------------


@OTHER_LOOPS
async def test_controller_in_another_loop_on_a_shared_reflector(other: str) -> None:
    api = FakeApi(ConfigMap)
    api.pages.append(Page([cm("a"), cm("b")], resource_version="1"))
    shared = SharedReflector(api.as_api())

    async def control() -> list[str]:
        controller = Controller.for_shared(ConfigMap, shared)
        names: list[str] = []
        with anyio.fail_after(_TIMEOUT):
            async with controller.running(_reconcile, _error_policy, None) as results:
                async for result in results:
                    names.append(result.obj_ref.name)
                    if len(names) == 2:
                        break
        return sorted(names)

    async with anyio.create_task_group() as group:
        group.start_soon(shared.run)
        assert await _LoopThread(control, other).result() == ["a", "b"]
        group.cancel_scope.cancel()


def test_a_shared_reflector_runs_once_across_threads() -> None:
    api = FakeApi(ConfigMap)
    api.pages.append(Page([], resource_version="1"))
    shared = SharedReflector(api.as_api())

    async def attempt() -> None:
        with anyio.move_on_after(0.5):
            await shared.run()

    outcomes = _race(attempt)
    refused = [error for error in outcomes if isinstance(error, RuntimeError)]
    assert len(refused) == _THREADS - 1, outcomes


def test_a_controller_runs_once_across_threads() -> None:
    shared = SharedReflector(FakeApi(ConfigMap).as_api())
    controller = Controller.for_shared(ConfigMap, shared)

    async def attempt() -> None:
        with anyio.move_on_after(0.5):
            async with controller.running(_reconcile, _error_policy, None):
                await anyio.sleep_forever()

    outcomes = _race(attempt)
    refused = [error for error in outcomes if isinstance(error, RuntimeError)]
    assert len(refused) == _THREADS - 1, outcomes


def test_a_backoff_counts_every_attempt_across_threads() -> None:
    per_thread = 2000
    backoff = ExponentialBackoff(jitter=False, max_retries=_THREADS * per_thread)
    barrier = threading.Barrier(_THREADS)
    counts: list[int] = []
    lock = threading.Lock()

    def take() -> None:
        barrier.wait()
        count = sum(backoff.next() is not None for _ in range(per_thread))
        with lock:
            counts.append(count)

    threads = [threading.Thread(target=take) for _ in range(_THREADS)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(_TIMEOUT)
    assert sum(counts) == _THREADS * per_thread
    assert backoff.next() is None
