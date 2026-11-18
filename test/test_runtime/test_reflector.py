"""``Store``, ``Writer`` and their subscriptions, ``reflector()`` and
``SharedReflector``."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Iterable

import anyio
import anyio.lowlevel
import pytest

from kubex.core.exceptions import (
    KubernetesError,
    KubexConnectionError,
    build_exception,
)
from kubex.k8s.v1_35.core.v1.config_map import ConfigMap
from kubex_core.models.metadata import ObjectMetadata
from kubex_runtime import (
    Apply,
    Bookmark,
    BoundedBuffer,
    Delete,
    Event,
    ExponentialBackoff,
    Init,
    InitApply,
    InitDone,
    MergedBuffer,
    ObjectRef,
    ReflectHandle,
    SharedReflector,
    Store,
    Writer,
    reflector,
    shared_reflector,
    store,
)
from test.test_runtime._fakes import FakeApi, Page, cm, event

pytestmark = pytest.mark.anyio

_TIMEOUT = 5


def _names(objects: Iterable[ConfigMap]) -> list[tuple[str | None, str | None]]:
    return [(obj.metadata.name, obj.metadata.resource_version) for obj in objects]


async def _list(writer: Writer[ConfigMap], *objects: ConfigMap) -> None:
    await writer.apply_watcher_event(Init())
    for obj in objects:
        await writer.apply_watcher_event(InitApply(obj))
    await writer.apply_watcher_event(InitDone())


async def _take(handle: ReflectHandle[ConfigMap], count: int) -> list[ConfigMap]:
    taken = []
    with anyio.fail_after(1):
        for _ in range(count):
            taken.append(await handle.__anext__())
    return taken


async def _nothing_pending(handle: ReflectHandle[ConfigMap]) -> None:
    with anyio.move_on_after(0.05) as scope:
        await handle.__anext__()
    assert scope.cancelled_caught, "the subscription had something to read"


async def _blocks(writer: Writer[ConfigMap], event: Event[ConfigMap]) -> bool:
    """Whether applying `event` waits (for a subscriber to make room)."""
    with anyio.move_on_after(0.05) as scope:
        await writer.apply_watcher_event(event)
    return scope.cancelled_caught


def _pair() -> tuple[Store[ConfigMap], Writer[ConfigMap]]:
    return store()


def _ref(name: str) -> ObjectRef:
    return ObjectRef.of(ConfigMap, name, "ns")


# -- store ----------------------------------------------------------------------


async def test_store_pair() -> None:
    reader, writer = _pair()
    assert writer.as_reader() is reader


async def test_relist_is_applied_at_its_end() -> None:
    writer: Writer[ConfigMap] = Writer()
    reader = writer.as_reader()
    with anyio.fail_after(_TIMEOUT):
        await writer.apply_watcher_event(Init())
        await writer.apply_watcher_event(InitApply(cm("a")))
        await writer.apply_watcher_event(InitApply(cm("b")))
        assert len(reader) == 0
        assert not reader.is_ready()
        await writer.apply_watcher_event(InitDone())
    assert reader.is_ready()
    assert sorted(_names(reader.state())) == [("a", "1"), ("b", "1")]


async def test_relist_replaces_the_store_atomically() -> None:
    writer: Writer[ConfigMap] = Writer()
    reader = writer.as_reader()
    with anyio.fail_after(_TIMEOUT):
        await _list(writer, cm("a", "1"), cm("b", "1"))
        await writer.apply_watcher_event(Init())
        await writer.apply_watcher_event(InitApply(cm("a", "2")))
        await writer.apply_watcher_event(InitApply(cm("c", "2")))
        # still the previous list until InitDone
        assert sorted(_names(reader.state())) == [("a", "1"), ("b", "1")]
        await writer.apply_watcher_event(InitDone())
    assert sorted(_names(reader.state())) == [("a", "2"), ("c", "2")]
    assert _ref("b") not in reader


async def test_relist_sends_listed_then_gone_objects() -> None:
    writer: Writer[ConfigMap] = Writer()
    with anyio.fail_after(_TIMEOUT):
        await _list(writer, cm("a", "1"), cm("b", "1"))
        handle = writer.subscribe(MergedBuffer())
        assert len(await _take(handle, 2)) == 2  # the snapshot
        await _list(writer, cm("a", "2"), cm("c", "2"))
        # listed objects first, then the last state of the ones no longer there
        assert _names(await _take(handle, 3)) == [("a", "2"), ("c", "2"), ("b", "1")]
        await _nothing_pending(handle)


@pytest.mark.parametrize("buffer", [BoundedBuffer(), MergedBuffer()])
async def test_relist_sends_an_object_re_created_under_its_name_as_gone(
    buffer: BoundedBuffer | MergedBuffer,
) -> None:
    writer: Writer[ConfigMap] = Writer()
    with anyio.fail_after(_TIMEOUT):
        await _list(writer, cm("a", "1", uid="old"))
        handle = writer.subscribe(buffer)
        assert len(await _take(handle, 1)) == 1  # the snapshot
        await _list(writer, cm("a", "2", uid="new"))
        taken = await _take(handle, 2)
        await _nothing_pending(handle)
    assert [(obj.metadata.uid, obj.metadata.resource_version) for obj in taken] == [
        ("new", "2"),
        ("old", "1"),
    ]


@pytest.mark.parametrize(
    ("deletion", "deleted"),
    [
        pytest.param([Delete(cm("a", "2"))], ("a", "2"), id="deleted"),
        pytest.param([Init(), InitDone()], ("a", "1"), id="gone-in-a-relist"),
        pytest.param(
            # cancelled on the listed object, before the gone one was sent
            [Init(), InitApply(cm("b", "2")), InitDone()],
            ("a", "1"),
            id="gone-behind-a-listed-one",
        ),
    ],
)
async def test_a_deletion_left_undelivered_by_a_cancelled_event_comes_at_the_next(
    deletion: list[Event[ConfigMap]], deleted: tuple[str, str]
) -> None:
    """Regression: a deletion cancelled while a bounded subscriber was full never
    reached the subscribers after it, and a later run's re-list could not send it
    again, as the store no longer had the object."""
    writer: Writer[ConfigMap] = Writer()
    with anyio.fail_after(_TIMEOUT):
        full = writer.subscribe(BoundedBuffer(size=1))
        later = writer.subscribe(MergedBuffer())
        await _list(writer, cm("a", "1"))
        assert _names(await _take(later, 1)) == [("a", "1")]
        # `full` has no room left: the event is cancelled waiting for it
        *before, last = deletion
        for event_ in before:
            await writer.apply_watcher_event(event_)
        assert await _blocks(writer, last)
        await _nothing_pending(later)
        # room again, and the next event: a later run's re-list starting, say
        assert _names(await _take(full, 1)) == [("a", "1")]
        async with anyio.create_task_group() as group:
            group.start_soon(writer.apply_watcher_event, Init())
            from_full = await _take(full, 1)
        from_later = await _take(later, 1)
        await _nothing_pending(full)
        await _nothing_pending(later)
    # once to each: `full` had not queued it when the event was cancelled
    assert _names(from_full) == [deleted]
    assert _names(from_later) == [deleted]


async def test_a_subscriber_closed_meanwhile_holds_up_no_owed_deletion() -> None:
    writer: Writer[ConfigMap] = Writer()
    with anyio.fail_after(_TIMEOUT):
        # first in line, and full: the deletion is cancelled waiting on it
        closed = writer.subscribe(BoundedBuffer(size=1))
        later = writer.subscribe(MergedBuffer())
        await _list(writer, cm("a", "1"))
        assert _names(await _take(later, 1)) == [("a", "1")]
        assert await _blocks(writer, Delete(cm("a", "2")))
        await _nothing_pending(later)
        closed.close()
        # the deletion goes on to the subscriber after the closed one
        assert not await _blocks(writer, Apply(cm("b", "3")))
        taken = await _take(later, 2)
        await _nothing_pending(later)
    assert _names(taken) == [("a", "2"), ("b", "3")]


async def test_an_event_cancelled_delivering_owed_deletions_is_still_applied() -> None:
    """Regression: owed deletions were delivered before the event was applied,
    so an event cancelled waiting to deliver them never reached the store (a
    cancelled `Init` left the re-list after it reporting every object gone)."""
    writer: Writer[ConfigMap] = Writer()
    reader = writer.as_reader()
    taken: list[ConfigMap] = []

    async def read(handle: ReflectHandle[ConfigMap]) -> None:
        async for obj in handle:
            taken.append(obj)

    with anyio.fail_after(_TIMEOUT):
        full = writer.subscribe(BoundedBuffer(size=1))
        await _list(writer, cm("a", "1"))
        assert await _blocks(writer, Delete(cm("a", "2")))
        # `full` still has no room: each waits to deliver the deletion
        assert await _blocks(writer, Apply(cm("b", "3")))
        assert reader.get(_ref("b")) is not None
        assert await _blocks(writer, Init())
        async with anyio.create_task_group() as group:
            group.start_soon(read, full)
            # the re-list the cancelled Init started
            await writer.apply_watcher_event(InitApply(cm("c", "4")))
            await writer.apply_watcher_event(InitDone())
            while len(taken) < 4:
                await anyio.sleep(0.001)
            group.cancel_scope.cancel()
    assert _names(reader.state()) == [("c", "4")]
    # the deletion before the re-list; b's own delivery was cancelled, so it
    # comes once, as gone
    assert _names(taken) == [("a", "1"), ("a", "2"), ("c", "4"), ("b", "3")]


async def test_a_reference_of_another_kind_finds_nothing() -> None:
    writer: Writer[ConfigMap] = Writer()
    reader = writer.as_reader()
    with anyio.fail_after(_TIMEOUT):
        await _list(writer, cm("a"))
    # same namespace and name, another kind or group: not the cached ConfigMap
    for other in (
        ObjectRef(group="core", kind="Secret", name="a", namespace="ns"),
        ObjectRef(group="example.com", kind="ConfigMap", name="a", namespace="ns"),
    ):
        assert reader.get(other) is None
        assert other not in reader
    assert reader.get(_ref("a")) is not None
    assert _ref("a") in reader


async def test_empty_first_list_makes_the_store_ready() -> None:
    writer: Writer[ConfigMap] = Writer()
    with anyio.fail_after(_TIMEOUT):
        await _list(writer)
    assert writer.as_reader().is_ready()
    assert len(writer.as_reader()) == 0


async def test_wait_until_ready() -> None:
    writer: Writer[ConfigMap] = Writer()
    reader = writer.as_reader()
    ready: list[bool] = []

    async def wait() -> None:
        await reader.wait_until_ready()
        ready.append(True)

    with anyio.fail_after(_TIMEOUT):
        async with anyio.create_task_group() as group:
            group.start_soon(wait)
            group.start_soon(wait)
            await anyio.sleep(0.05)
            assert ready == []
            await writer.apply_watcher_event(Init())
            await writer.apply_watcher_event(InitApply(cm("a")))
            await anyio.sleep(0.02)
            assert ready == []
            await writer.apply_watcher_event(InitDone())
        assert ready == [True, True]
        # ready already: returns at once
        await reader.wait_until_ready()


async def test_apply_and_delete() -> None:
    writer: Writer[ConfigMap] = Writer()
    reader = writer.as_reader()
    with anyio.fail_after(_TIMEOUT):
        await _list(writer)
        await writer.apply_watcher_event(Apply(cm("a", "1")))
        await writer.apply_watcher_event(Apply(cm("b", "1", namespace="other")))
        await writer.apply_watcher_event(Apply(cm("a", "2")))
        assert len(reader) == 2
        found = reader.get(_ref("a"))
        assert found is not None
        assert found.metadata.resource_version == "2"
        assert reader.get_named("other", "b") is not None
        assert reader.get_named("ns", "b") is None
        assert _names(reader.namespaced("other")) == [("b", "1")]
        assert _names(reader.find(lambda obj: obj.metadata.name == "a")) == [("a", "2")]
        await writer.apply_watcher_event(Delete(cm("a", "3")))
    assert reader.get(_ref("a")) is None
    assert _ref("a") not in reader
    assert reader.namespaced("ns") == []
    assert len(reader) == 1


async def test_delete_of_an_unknown_object_is_ignored() -> None:
    writer: Writer[ConfigMap] = Writer()
    with anyio.fail_after(_TIMEOUT):
        await _list(writer, cm("a"))
        await writer.apply_watcher_event(Delete(cm("missing")))
        await writer.apply_watcher_event(Delete(cm("missing", namespace="nowhere")))
    assert len(writer.as_reader()) == 1


async def test_init_apply_without_init_is_ignored() -> None:
    writer: Writer[ConfigMap] = Writer()
    with anyio.fail_after(_TIMEOUT):
        await _list(writer, cm("a"))
        await writer.apply_watcher_event(InitApply(cm("stray")))
    assert _names(writer.as_reader().state()) == [("a", "1")]


async def test_nameless_object_is_rejected() -> None:
    writer: Writer[ConfigMap] = Writer()
    with anyio.fail_after(_TIMEOUT), pytest.raises(ValueError, match="no name"):
        await writer.apply_watcher_event(
            Apply(ConfigMap(metadata=ObjectMetadata(namespace="ns")))
        )


# -- recorded writes ----------------------------------------------------------------

PARENT = cm("parent", uid="uid-parent")


async def _seen(store: Store[ConfigMap], owner: ConfigMap = PARENT) -> bool:
    """Whether the store has seen every write recorded for `owner`."""
    with anyio.move_on_after(0.05) as scope:
        await store.wait_for_writes(owner)
    return not scope.cancelled_caught


async def _wrote_at_10() -> tuple[Store[ConfigMap], Writer[ConfigMap]]:
    """A store listed at version 5, with a child written at 10 for PARENT."""
    reader, writer = _pair()
    await writer.apply_watcher_event(Init())
    await writer.apply_watcher_event(InitDone("5"))
    reader.wrote(cm("child", "10"), owner=PARENT)
    assert not await _seen(reader)
    return reader, writer


async def test_a_write_is_waited_for_until_the_store_applies_it() -> None:
    reader, writer = await _wrote_at_10()
    await writer.apply_watcher_event(Apply(cm("child", "10")))
    assert await _seen(reader)


@pytest.mark.parametrize(
    "events",
    [
        [Apply(cm("other", "11"))],
        [Delete(cm("other", "11"))],
        [Bookmark("11")],
        [Init(), InitDone("11")],
    ],
    ids=["apply", "delete", "bookmark", "relist"],
)
async def test_a_later_version_of_any_object_shows_the_write_seen(
    events: list[Event[ConfigMap]],
) -> None:
    reader, writer = await _wrote_at_10()
    for e in events:
        await writer.apply_watcher_event(e)
    assert await _seen(reader)


async def test_a_relist_shows_the_write_only_at_its_end() -> None:
    reader, writer = await _wrote_at_10()
    await writer.apply_watcher_event(Init())
    await writer.apply_watcher_event(InitApply(cm("child", "10")))
    assert not await _seen(reader)
    await writer.apply_watcher_event(InitDone("10"))
    assert await _seen(reader)


async def test_a_relist_older_than_the_write_keeps_it_waited_for() -> None:
    reader, writer = await _wrote_at_10()
    await writer.apply_watcher_event(Init())
    await writer.apply_watcher_event(InitApply(cm("child", "8")))
    await writer.apply_watcher_event(InitDone("8"))
    assert not await _seen(reader)
    await writer.apply_watcher_event(Apply(cm("child", "10")))
    assert await _seen(reader)


async def test_a_relist_at_the_store_version_keeps_the_write_waited_for() -> None:
    reader, writer = await _wrote_at_10()
    await writer.apply_watcher_event(Init())
    await writer.apply_watcher_event(InitDone("5"))
    assert not await _seen(reader)


async def test_a_relist_below_the_store_sets_it_back() -> None:
    # another cluster's list, or one restored from an etcd snapshot
    reader, writer = _pair()
    await writer.apply_watcher_event(Bookmark("100"))
    await writer.apply_watcher_event(Init())
    await writer.apply_watcher_event(InitDone("8"))
    reader.wrote(cm("child", "50"), owner=PARENT)
    assert not await _seen(reader)
    await writer.apply_watcher_event(Apply(cm("child", "50")))
    assert await _seen(reader)


async def test_a_relist_below_the_store_drops_the_writes_recorded() -> None:
    reader, writer = await _wrote_at_10()
    await writer.apply_watcher_event(Bookmark("9"))
    with anyio.fail_after(_TIMEOUT):
        async with anyio.create_task_group() as group:
            group.start_soon(reader.wait_for_writes, PARENT)
            await anyio.wait_all_tasks_blocked()
            # writes of the old history, which the store will never see
            await writer.apply_watcher_event(Init())
            await writer.apply_watcher_event(InitDone("3"))
    assert reader._written == {}
    assert reader._written_heap == []


async def test_a_relist_without_a_version_keeps_the_write_waited_for() -> None:
    reader, writer = await _wrote_at_10()
    await _list(writer, cm("child", "10"))
    assert not await _seen(reader)


async def test_a_relist_without_a_version_leaves_the_store_without_one() -> None:
    # it may be another history's: no write counts as seen against the old one
    reader, writer = _pair()
    await writer.apply_watcher_event(Bookmark("20"))
    await _list(writer)
    reader.wrote(cm("child", "15"), owner=PARENT)
    assert not await _seen(reader)
    await writer.apply_watcher_event(Bookmark("15"))
    assert await _seen(reader)


async def test_an_older_event_keeps_the_write_waited_for() -> None:
    reader, writer = await _wrote_at_10()
    await writer.apply_watcher_event(Apply(cm("child", "9")))
    await writer.apply_watcher_event(Bookmark("9"))
    assert not await _seen(reader)


async def test_a_write_the_store_has_seen_is_not_waited_for() -> None:
    reader, writer = _pair()
    await writer.apply_watcher_event(Bookmark("20"))
    # an older event does not move the store back
    await writer.apply_watcher_event(Apply(cm("child", "3")))
    reader.wrote(cm("child", "15"), owner=PARENT)
    assert await _seen(reader)


async def test_the_later_of_two_writes_is_waited_for() -> None:
    reader, writer = await _wrote_at_10()
    reader.wrote(cm("child", "20"), owner=PARENT)
    reader.wrote(cm("child", "15"), owner=PARENT)
    await writer.apply_watcher_event(Bookmark("19"))
    assert not await _seen(reader)
    await writer.apply_watcher_event(Bookmark("20"))
    assert await _seen(reader)
    assert reader._written == {}


async def test_writes_are_dropped_as_the_store_reaches_them() -> None:
    other = cm("other-parent", uid="uid-other")
    reader, writer = await _wrote_at_10()
    reader.wrote(cm("other-child", "12"), owner=other)
    reader.wrote(cm("child", "20"), owner=PARENT)
    await writer.apply_watcher_event(Bookmark("12"))
    # nothing has read them since: the store dropped them as it advanced, and
    # kept the owner a later write raised past it
    assert reader._written == {"uid-parent": 20}
    assert reader._written_heap == [(20, "uid-parent")]
    await writer.apply_watcher_event(Bookmark("20"))
    assert reader._written == {}
    assert reader._written_heap == []


async def test_writes_are_kept_per_owner() -> None:
    other = cm("other-parent", uid="uid-other")
    reader, writer = await _wrote_at_10()
    reader.wrote(cm("other-child", "12"), owner=other)
    await writer.apply_watcher_event(Bookmark("11"))
    assert await _seen(reader)
    assert not await _seen(reader, other)
    # an owner that wrote nothing waits for nothing
    assert await _seen(reader, cm("idle", uid="uid-idle"))


async def test_an_owner_without_a_uid_is_rejected() -> None:
    reader, _ = _pair()
    with pytest.raises(ValueError, match="has no uid"):
        reader.wrote(cm("child", "10"), owner=cm("parent"))


async def test_an_opaque_version_is_not_recorded_and_warns_once(
    caplog: pytest.LogCaptureFixture,
) -> None:
    reader, writer = await _wrote_at_10()
    with caplog.at_level(logging.WARNING, logger="kubex_runtime.reflector"):
        reader.wrote(cm("child", "a1"), owner=cm("p", uid="uid-p"))
        reader.wrote(cm("child", "a2"), owner=cm("p", uid="uid-p"))
    [record] = [r for r in caplog.records if "not an integer" in r.getMessage()]
    assert record.name == "kubex_runtime.reflector"
    assert await _seen(reader, cm("p", uid="uid-p"))
    # nor does an opaque version move the store
    await writer.apply_watcher_event(Bookmark("a3"))
    assert not await _seen(reader)


async def test_wait_for_writes_returns_once_the_write_is_applied() -> None:
    reader, writer = await _wrote_at_10()
    with anyio.fail_after(_TIMEOUT):
        async with anyio.create_task_group() as group:
            group.start_soon(reader.wait_for_writes, PARENT)
            await anyio.wait_all_tasks_blocked()
            await writer.apply_watcher_event(Apply(cm("child", "10")))


async def test_a_bookmark_changes_and_delivers_nothing() -> None:
    reader, writer = _pair()
    await _list(writer, cm("a", "1"))
    async with writer.subscribe(MergedBuffer()) as handle:
        await _take(handle, 1)  # the store's contents
        await writer.apply_watcher_event(Bookmark("7"))
        await _nothing_pending(handle)
    assert _names(reader.state()) == [("a", "1")]


async def test_shared_reflector_records_writes_in_its_store() -> None:
    shared = SharedReflector(FakeApi(ConfigMap).as_api())
    shared.wrote(cm("child", "10"), owner=PARENT)
    assert not await _seen(shared.store)
    shared.forget_writes()
    assert await _seen(shared.store)


async def test_forget_writes_drops_the_writes_of_every_owner() -> None:
    other = cm("other-parent", uid="uid-other")
    reader, _ = await _wrote_at_10()
    reader.wrote(cm("other-child", "12"), owner=other)
    reader.forget_writes()
    assert await _seen(reader)
    assert await _seen(reader, other)
    assert reader._written == {}
    assert reader._written_heap == []


async def test_forget_writes_releases_a_waiting_task() -> None:
    reader, _ = await _wrote_at_10()
    with anyio.fail_after(_TIMEOUT):
        async with anyio.create_task_group() as group:
            group.start_soon(reader.wait_for_writes, PARENT)
            await anyio.wait_all_tasks_blocked()
            reader.forget_writes()


async def test_writes_after_forget_writes_are_waited_for_as_usual() -> None:
    reader, writer = await _wrote_at_10()
    await writer.apply_watcher_event(Bookmark("8"))
    reader.forget_writes()
    # the store's version went with them (another cluster's do not compare
    # with it): a write below it is waited for too, until a list shows it
    reader.wrote(cm("child", "7"), owner=PARENT)
    assert not await _seen(reader)
    await writer.apply_watcher_event(Init())
    await writer.apply_watcher_event(InitDone("7"))
    assert await _seen(reader)
    reader.wrote(cm("child", "20"), owner=PARENT)
    assert not await _seen(reader)
    await writer.apply_watcher_event(Apply(cm("child", "20")))
    assert await _seen(reader)


# -- subscriptions ----------------------------------------------------------------


@pytest.mark.parametrize("buffer", [None, BoundedBuffer(), MergedBuffer()])
async def test_subscriber_gets_changes_after_they_are_applied(
    buffer: BoundedBuffer | MergedBuffer | None,
) -> None:
    writer: Writer[ConfigMap] = Writer()
    reader = writer.as_reader()
    handle = writer.subscribe(buffer)
    with anyio.fail_after(_TIMEOUT):
        await _list(writer, cm("a"), cm("b"))
        listed = await _take(handle, 2)
        assert sorted(_names(listed)) == [("a", "1"), ("b", "1")]
        await writer.apply_watcher_event(Apply(cm("c")))
        (applied,) = await _take(handle, 1)
        assert applied.metadata.name == "c"
        assert _ref("c") in reader
        await writer.apply_watcher_event(Delete(cm("a", "9")))
        (deleted,) = await _take(handle, 1)
        assert _names([deleted]) == [("a", "9")]
        assert _ref("a") not in reader
        await _nothing_pending(handle)


async def test_subscriber_sees_nothing_of_an_unfinished_list() -> None:
    writer: Writer[ConfigMap] = Writer()
    handle = writer.subscribe()
    with anyio.fail_after(_TIMEOUT):
        await writer.apply_watcher_event(Init())
        await writer.apply_watcher_event(InitApply(cm("a")))
        await _nothing_pending(handle)


@pytest.mark.parametrize("buffer", [BoundedBuffer(size=1), MergedBuffer()])
async def test_late_subscriber_gets_the_store_first(
    buffer: BoundedBuffer | MergedBuffer,
) -> None:
    writer: Writer[ConfigMap] = Writer()
    with anyio.fail_after(_TIMEOUT):
        await _list(writer, cm("a"), cm("b"), cm("c"))
        # the snapshot is not limited by the buffer size, nor makes it wait
        handle = writer.subscribe(buffer)
        await writer.apply_watcher_event(Apply(cm("d")))
        taken = await _take(handle, 4)
    assert sorted(_names(taken[:3])) == [("a", "1"), ("b", "1"), ("c", "1")]
    assert _names(taken[3:]) == [("d", "1")]


async def test_subscriber_before_ready_gets_no_snapshot() -> None:
    writer: Writer[ConfigMap] = Writer()
    handle = writer.subscribe()
    with anyio.fail_after(_TIMEOUT):
        await _nothing_pending(handle)


async def test_every_subscriber_gets_every_change() -> None:
    writer: Writer[ConfigMap] = Writer()
    first = writer.subscribe()
    second = writer.subscribe(MergedBuffer())
    with anyio.fail_after(_TIMEOUT):
        await _list(writer, cm("a"))
        await writer.apply_watcher_event(Apply(cm("b")))
        assert _names(await _take(first, 2)) == [("a", "1"), ("b", "1")]
        assert _names(await _take(second, 2)) == [("a", "1"), ("b", "1")]


def test_a_subscription_kind_must_implement_its_methods() -> None:
    with pytest.raises(TypeError, match="abstract"):
        ReflectHandle(Writer[ConfigMap]())  # type: ignore[abstract]


def test_bounded_buffer_default_size() -> None:
    assert BoundedBuffer().size == 1024


@pytest.mark.parametrize("size", [0, -1])
def test_bounded_buffer_size_must_be_positive(size: int) -> None:
    with pytest.raises(ValueError, match="at least 1"):
        BoundedBuffer(size=size)


async def test_default_subscription_is_bounded_at_1024() -> None:
    writer: Writer[ConfigMap] = Writer()
    handle = writer.subscribe()
    with anyio.fail_after(_TIMEOUT):
        await _list(writer)
        for index in range(1024):
            await writer.apply_watcher_event(Apply(cm(f"o{index}")))
        assert await _blocks(writer, Apply(cm("one-too-many")))
        await handle.aclose()


async def test_bounded_subscriber_holds_up_the_writer() -> None:
    writer: Writer[ConfigMap] = Writer()
    reader = writer.as_reader()
    handle = writer.subscribe(BoundedBuffer(size=2))
    done = anyio.Event()

    async def write() -> None:
        for name in ("a", "b", "c"):
            await writer.apply_watcher_event(Apply(cm(name)))
        done.set()

    with anyio.fail_after(_TIMEOUT):
        await _list(writer)
        async with anyio.create_task_group() as group:
            group.start_soon(write)
            await anyio.sleep(0.05)
            # a and b fill the queue; c is in the store, the writer waits to send it
            assert not done.is_set()
            assert _ref("c") in reader
            assert _names(await _take(handle, 1)) == [("a", "1")]
            await done.wait()
        assert _names(await _take(handle, 2)) == [("b", "1"), ("c", "1")]


async def test_a_subscriber_joining_a_relist_delivery_gets_the_store_once() -> None:
    writer: Writer[ConfigMap] = Writer()
    with anyio.fail_after(_TIMEOUT):
        await _list(writer, cm("gone"))
        slow = writer.subscribe(BoundedBuffer(size=1))
        assert _names(await _take(slow, 1)) == [("gone", "1")]  # its snapshot
    done = anyio.Event()

    async def relist() -> None:
        await _list(writer, cm("a"), cm("b"), cm("c"))
        done.set()

    with anyio.fail_after(_TIMEOUT):
        async with anyio.create_task_group() as group:
            group.start_soon(relist)
            await anyio.sleep(0.05)
            # a fills the slow queue: the writer waits to send b
            assert not done.is_set()
            late = writer.subscribe()
            assert _names(await _take(slow, 4)) == [
                ("a", "1"),
                ("b", "1"),
                ("c", "1"),
                ("gone", "1"),
            ]
            await done.wait()
        # the store it joined, and nothing of the delivery under way: not c
        # again, nor the object that was gone before it subscribed
        assert sorted(_names(await _take(late, 3))) == [
            ("a", "1"),
            ("b", "1"),
            ("c", "1"),
        ]
        await _nothing_pending(late)
        await slow.aclose()
        await late.aclose()


async def test_slow_bounded_subscriber_holds_up_the_others() -> None:
    writer: Writer[ConfigMap] = Writer()
    slow = writer.subscribe(BoundedBuffer(size=1))
    fast = writer.subscribe(MergedBuffer())
    with anyio.fail_after(_TIMEOUT):
        await _list(writer)
        await writer.apply_watcher_event(Apply(cm("a")))
        assert await _blocks(writer, Apply(cm("b")))
        assert _names(await _take(fast, 1)) == [("a", "1")]
        await slow.aclose()


@pytest.mark.parametrize("buffer", [BoundedBuffer(size=1), MergedBuffer()])
async def test_closed_subscription_is_dropped(
    buffer: BoundedBuffer | MergedBuffer,
) -> None:
    writer: Writer[ConfigMap] = Writer()
    other = writer.subscribe(MergedBuffer())
    handle = writer.subscribe(buffer)
    with anyio.fail_after(_TIMEOUT):
        await _list(writer)
        handle.close()
        for name in ("a", "b", "c"):
            assert not await _blocks(writer, Apply(cm(name)))
        assert len(await _take(other, 3)) == 3
        with pytest.raises(StopAsyncIteration):
            await handle.__anext__()


async def test_closing_wakes_a_writer_waiting_on_it() -> None:
    writer: Writer[ConfigMap] = Writer()
    handle = writer.subscribe(BoundedBuffer(size=1))
    done = anyio.Event()

    async def write() -> None:
        await writer.apply_watcher_event(Apply(cm("a")))
        await writer.apply_watcher_event(Apply(cm("b")))  # waits: the queue is full
        done.set()

    with anyio.fail_after(_TIMEOUT):
        await _list(writer)
        async with anyio.create_task_group() as group:
            group.start_soon(write)
            await anyio.sleep(0.05)
            assert not done.is_set()
            handle.close()
            await done.wait()
        # dropped: no more waiting
        assert not await _blocks(writer, Apply(cm("c")))


@pytest.mark.parametrize("buffer", [BoundedBuffer(size=4), MergedBuffer()])
async def test_close_drops_what_is_buffered(
    buffer: BoundedBuffer | MergedBuffer,
) -> None:
    writer: Writer[ConfigMap] = Writer()
    with anyio.fail_after(_TIMEOUT):
        await _list(writer, cm("a"))
        handle = writer.subscribe(buffer)  # snapshot: a
        await writer.apply_watcher_event(Apply(cm("b")))
        await handle.aclose()
        assert [obj async for obj in handle] == []


@pytest.mark.parametrize("buffer", [BoundedBuffer(), MergedBuffer()])
async def test_close_ends_a_waiting_reader(
    buffer: BoundedBuffer | MergedBuffer,
) -> None:
    writer: Writer[ConfigMap] = Writer()
    handle = writer.subscribe(buffer)
    read: list[ConfigMap] = []

    async def read_all() -> None:
        async for obj in handle:
            read.append(obj)

    with anyio.fail_after(_TIMEOUT):
        async with anyio.create_task_group() as group:
            group.start_soon(read_all)
            await anyio.sleep(0.05)
            handle.close()
    assert read == []


@pytest.mark.parametrize("buffer", [BoundedBuffer(), MergedBuffer()])
async def test_close_is_idempotent(buffer: BoundedBuffer | MergedBuffer) -> None:
    writer: Writer[ConfigMap] = Writer()
    handle = writer.subscribe(buffer)
    handle.close()
    await handle.aclose()
    handle.close()
    with anyio.fail_after(_TIMEOUT):
        await _list(writer, cm("a"))


@pytest.mark.parametrize("buffer", [BoundedBuffer(), MergedBuffer()])
async def test_async_with_closes_the_subscription(
    buffer: BoundedBuffer | MergedBuffer,
) -> None:
    writer: Writer[ConfigMap] = Writer()
    with anyio.fail_after(_TIMEOUT):
        await _list(writer)
        async with writer.subscribe(buffer) as handle:
            await writer.apply_watcher_event(Apply(cm("a")))
            assert _names(await _take(handle, 1)) == [("a", "1")]
        await writer.apply_watcher_event(Apply(cm("b")))
        assert [obj async for obj in handle] == []


async def test_async_iteration() -> None:
    writer: Writer[ConfigMap] = Writer()
    handle = writer.subscribe()
    with anyio.fail_after(_TIMEOUT):
        await _list(writer, cm("a"), cm("b"))
        names: list[str] = []
        async for obj in handle:
            names.append(obj.metadata.name or "")
            if len(names) == 2:
                break
    assert sorted(names) == ["a", "b"]


# -- merged subscriptions -----------------------------------------------------------


async def test_merged_keeps_the_latest_state_in_the_first_place() -> None:
    writer: Writer[ConfigMap] = Writer()
    handle = writer.subscribe(MergedBuffer())
    with anyio.fail_after(_TIMEOUT):
        await _list(writer)
        await writer.apply_watcher_event(Apply(cm("a", "1")))
        await writer.apply_watcher_event(Apply(cm("b", "1")))
        await writer.apply_watcher_event(Apply(cm("a", "2")))
        await writer.apply_watcher_event(Apply(cm("a", "3")))
        assert _names(await _take(handle, 2)) == [("a", "3"), ("b", "1")]
        await _nothing_pending(handle)


async def test_merged_keys_by_namespace_and_name() -> None:
    writer: Writer[ConfigMap] = Writer()
    handle = writer.subscribe(MergedBuffer())
    with anyio.fail_after(_TIMEOUT):
        await _list(writer)
        await writer.apply_watcher_event(Apply(cm("a", namespace="one")))
        await writer.apply_watcher_event(Apply(cm("a", namespace="two")))
        taken = await _take(handle, 2)
    assert [obj.metadata.namespace for obj in taken] == ["one", "two"]


async def test_merged_keeps_a_deletion_apart_from_a_re_creation() -> None:
    writer: Writer[ConfigMap] = Writer()
    handle = writer.subscribe(MergedBuffer())
    with anyio.fail_after(_TIMEOUT):
        await _list(writer)
        await writer.apply_watcher_event(Apply(cm("a", "1", uid="old")))
        await writer.apply_watcher_event(Delete(cm("a", "2", uid="old")))
        # the same name again: another object
        await writer.apply_watcher_event(Apply(cm("a", "3", uid="new")))
        await writer.apply_watcher_event(Apply(cm("a", "4", uid="new")))
        taken = await _take(handle, 2)
        await _nothing_pending(handle)
    assert [(obj.metadata.uid, obj.metadata.resource_version) for obj in taken] == [
        ("old", "2"),
        ("new", "4"),
    ]


async def test_merged_never_holds_up_the_writer() -> None:
    writer: Writer[ConfigMap] = Writer()
    handle = writer.subscribe(MergedBuffer())
    with anyio.fail_after(_TIMEOUT):
        await _list(writer)
        for index in range(3000):
            assert not await _blocks(writer, Apply(cm(f"o{index % 10}", str(index))))
        taken = await _take(handle, 10)
        await _nothing_pending(handle)
    # one entry per object, each at its latest state
    assert _names(taken) == [(f"o{i}", str(2990 + i)) for i in range(10)]


async def test_merged_delete_brings_the_last_state() -> None:
    writer: Writer[ConfigMap] = Writer()
    reader = writer.as_reader()
    handle = writer.subscribe(MergedBuffer())
    with anyio.fail_after(_TIMEOUT):
        await _list(writer)
        await writer.apply_watcher_event(Apply(cm("a", "1")))
        await writer.apply_watcher_event(Delete(cm("a", "2")))
        assert _names(await _take(handle, 1)) == [("a", "2")]
        await _nothing_pending(handle)
    assert _ref("a") not in reader


async def test_merged_wakes_a_waiting_reader() -> None:
    writer: Writer[ConfigMap] = Writer()
    handle = writer.subscribe(MergedBuffer())
    read: list[ConfigMap] = []

    async def read_one() -> None:
        read.append(await handle.__anext__())

    with anyio.fail_after(_TIMEOUT):
        await _list(writer)
        async with anyio.create_task_group() as group:
            group.start_soon(read_one)
            await anyio.sleep(0.05)
            await writer.apply_watcher_event(Apply(cm("a")))
    assert _names(read) == [("a", "1")]


# -- reflector() --------------------------------------------------------------------


class _Source:
    """An event stream that records whether it was closed."""

    def __init__(self, events: list[Event[ConfigMap]], *, then_wait: bool) -> None:
        self.events = events
        self.then_wait = then_wait
        self.closed = False

    async def stream(self) -> AsyncIterator[Event[ConfigMap]]:
        try:
            for item in self.events:
                await anyio.lowlevel.checkpoint()
                yield item
            if self.then_wait:
                await anyio.sleep_forever()
        finally:
            self.closed = True


async def test_reflector_applies_and_passes_events_on() -> None:
    reader, writer = _pair()
    events: list[Event[ConfigMap]] = [
        Init(),
        InitApply(cm("a")),
        InitDone(),
        Apply(cm("b")),
        Delete(cm("a", "2")),
    ]
    source = _Source(events, then_wait=False)
    with anyio.fail_after(_TIMEOUT):
        passed = [event async for event in reflector(writer, source.stream())]
    assert passed == events
    assert _names(reader.state()) == [("b", "1")]
    assert source.closed


async def test_reflector_applies_before_passing_on() -> None:
    reader, writer = _pair()
    source = _Source([Init(), InitApply(cm("a")), InitDone()], then_wait=True)
    with anyio.fail_after(_TIMEOUT):
        stream = reflector(writer, source.stream())
        async for event in stream:
            if isinstance(event, InitDone):
                assert reader.is_ready()
                assert _ref("a") in reader
                break
        await stream.aclose()  # type: ignore[attr-defined]


async def test_reflector_closes_its_upstream() -> None:
    _, writer = _pair()
    source = _Source([Init(), InitDone(), Apply(cm("a"))], then_wait=True)
    with anyio.fail_after(_TIMEOUT):
        stream = reflector(writer, source.stream())
        async for event in stream:
            if isinstance(event, InitDone):
                break
        assert not source.closed
        await stream.aclose()  # type: ignore[attr-defined]
    assert source.closed


async def test_reflector_closes_its_upstream_when_cancelled() -> None:
    _, writer = _pair()
    source = _Source([Init(), InitDone()], then_wait=True)

    async def drain() -> None:
        async for _ in reflector(writer, source.stream()):
            pass

    with anyio.fail_after(_TIMEOUT):
        async with anyio.create_task_group() as group:
            group.start_soon(drain)
            await writer.as_reader().wait_until_ready()
            group.cancel_scope.cancel()
    assert source.closed


async def test_shared_reflector_fills_its_store_and_feeds_subscribers() -> None:
    api = FakeApi(ConfigMap)
    api.pages.append(Page([cm("a", "1")], resource_version="1"))
    api.watches.append([event("MODIFIED", cm("a", "2"))])
    with anyio.fail_after(_TIMEOUT):
        async with shared_reflector(api.as_api()) as shared:
            # made before the watch starts: it gets the list, then the change
            handle = shared.subscribe()
            assert _names(await _take(handle, 2)) == [("a", "1"), ("a", "2")]
            assert _names(shared.store.state()) == [("a", "2")]
            assert api.open_watches == 1
    # leaving the block stops the watch
    assert api.open_watches == 0


async def test_shared_reflector_whose_watcher_gives_up_ends_the_block() -> None:
    api = FakeApi(ConfigMap)
    api.pages.append(build_exception(500, "boom"))
    cancelled = False
    with anyio.fail_after(_TIMEOUT), pytest.raises(KubernetesError):
        async with shared_reflector(
            api.as_api(),
            backoff=ExponentialBackoff(initial=0, jitter=False, max_retries=0),
        ):
            try:
                await anyio.sleep_forever()
            except anyio.get_cancelled_exc_class():
                cancelled = True
                raise
    assert cancelled


async def test_shared_reflector_error_keeps_its_cause() -> None:
    cause = OSError("connection reset")
    error = KubexConnectionError("connecting failed")
    error.__cause__ = cause
    api = FakeApi(ConfigMap)
    api.pages.append(error)
    with anyio.fail_after(_TIMEOUT), pytest.raises(KubexConnectionError) as raised:
        async with shared_reflector(
            api.as_api(),
            backoff=ExponentialBackoff(initial=0, jitter=False, max_retries=0),
        ):
            await anyio.sleep_forever()
    assert raised.value is error
    assert raised.value.__cause__ is cause


async def test_shared_reflector_run_again_starts_its_backoff_over() -> None:
    api = FakeApi(ConfigMap)
    # first run: fails, retries once, fails again and gives up
    api.pages.append(build_exception(500, "boom"))
    api.pages.append(build_exception(500, "boom"))
    # second run: fails, retries once and lists
    api.pages.append(build_exception(500, "boom"))
    api.pages.append(Page([cm("a")], resource_version="1"))
    shared = SharedReflector(
        api.as_api(),
        backoff=ExponentialBackoff(initial=0, jitter=False, max_retries=1),
    )
    with anyio.fail_after(_TIMEOUT):
        with pytest.raises(KubernetesError):
            await shared.run()
        async with anyio.create_task_group() as group:
            group.start_soon(shared.run)
            await shared.store.wait_until_ready()
            group.cancel_scope.cancel()
    assert _names(shared.store.state()) == [("a", "1")]
    assert len(api.list_calls) == 4


async def test_shared_reflector_runs_one_watch_at_a_time() -> None:
    api = FakeApi(ConfigMap)
    api.pages.append(Page([cm("a")], resource_version="1"))
    api.pages.append(Page([cm("b")], resource_version="2"))
    shared = SharedReflector(api.as_api())
    with anyio.fail_after(_TIMEOUT):
        async with anyio.create_task_group() as group:
            group.start_soon(shared.run)
            await shared.store.wait_until_ready()
            with pytest.raises(RuntimeError, match="already running"):
                await shared.run()
            group.cancel_scope.cancel()
        assert api.open_watches == 0
        # run again once it ended, it lists anew
        async with anyio.create_task_group() as group:
            group.start_soon(shared.run)
            while shared.store.get_named("ns", "b") is None:
                await anyio.sleep(0.001)
            group.cancel_scope.cancel()
    assert _names(shared.store.state()) == [("b", "1")]
