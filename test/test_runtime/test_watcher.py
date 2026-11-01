"""``watcher()``: list paging, watching, re-listing, retries and the stall watchdog."""

from __future__ import annotations

import importlib
import logging
from collections.abc import AsyncIterator, Callable
from typing import Any, AsyncGenerator, cast

import anyio
import pytest
from pydantic import ValidationError

from kubex.core.exceptions import (
    Gone,
    KubernetesError,
    KubexClientException,
    KubexTimeoutError,
    UnprocessableEntity,
    build_exception,
)
from kubex.core.invalid_object import InvalidObject
from kubex.core.params import InvalidObjects, Timeout
from kubex.core.watch_event import EventType, InvalidWatchEvent
from kubex.k8s.v1_35.core.v1.config_map import ConfigMap
from kubex_core.models.metadata import ObjectMetadata
from kubex_runtime import (
    Apply,
    Bookmark,
    Delete,
    Event,
    ExponentialBackoff,
    Init,
    InitApply,
    InitDone,
    InitialListStrategy,
    WatcherConfig,
    watcher,
)

from ._fakes import BLOCK, FakeApi, Page, bookmark, cm, event

pytestmark = pytest.mark.anyio

# the package exports a `watcher` function that hides the module of that name
WATCHER_MODULE = importlib.import_module("kubex_runtime.watcher")


class RecordingBackoff:
    """Never waits; counts its calls; gives up after `max_retries` if set."""

    def __init__(self, max_retries: int | None = None) -> None:
        self.max_retries = max_retries
        self.attempts = 0
        self.next_calls = 0
        self.resets = 0

    def next(self) -> float | None:
        self.next_calls += 1
        if self.max_retries is not None and self.attempts >= self.max_retries:
            return None
        self.attempts += 1
        return 0.0

    def reset(self) -> None:
        self.resets += 1
        self.attempts = 0


def describe(events: list[Event[ConfigMap]]) -> list[tuple[str, ...]]:
    out: list[tuple[str, ...]] = []
    for e in events:
        match e:
            case Init():
                out.append(("Init",))
            case InitDone():
                out.append(("InitDone",))
            case Bookmark(version):
                out.append(("Bookmark", version))
            case InitApply(obj) | Apply(obj) | Delete(obj):
                out.append(
                    (
                        type(e).__name__,
                        obj.metadata.name or "",
                        obj.metadata.resource_version or "",
                    )
                )
    return out


async def take(
    stream: AsyncIterator[Event[ConfigMap]], count: int
) -> list[Event[ConfigMap]]:
    """The first `count` events of `stream`, which is then closed."""
    generator = cast(AsyncGenerator[Event[ConfigMap], None], stream)
    events: list[Event[ConfigMap]] = []
    try:
        async for e in generator:
            events.append(e)
            if len(events) >= count:
                break
    finally:
        await generator.aclose()
    return events


async def run_until(
    stream: AsyncIterator[Event[ConfigMap]], done: Callable[[], bool]
) -> list[Event[ConfigMap]]:
    """Drains `stream` in a task until `done()`, then cancels it."""
    events: list[Event[ConfigMap]] = []

    async def drain() -> None:
        async for e in stream:
            events.append(e)

    async with anyio.create_task_group() as group:
        group.start_soon(drain)
        while not done():
            await anyio.sleep(0.001)
        group.cancel_scope.cancel()
    return events


def invalid_event(name: str, rv: str) -> InvalidWatchEvent:
    raw: dict[str, Any] = {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {"name": name, "namespace": "ns", "resourceVersion": rv},
        "data": 5,
    }
    try:
        ConfigMap.model_validate(raw)
    except ValidationError as error:
        metadata = ObjectMetadata.model_validate(raw["metadata"])
        return InvalidWatchEvent(EventType.ADDED, InvalidObject(raw, error, metadata))
    raise AssertionError("expected the object not to fit ConfigMap")


async def test_lists_every_page_then_watches_from_the_list_version() -> None:
    api = FakeApi(ConfigMap)
    api.pages.extend(
        [
            Page([cm("a", "1")], continue_="c1"),
            Page([cm("b", "2")], resource_version="7"),
        ]
    )
    api.watches.append(
        [
            event("ADDED", cm("c", "8")),
            event("MODIFIED", cm("a", "9")),
            event("DELETED", cm("b", "10")),
            BLOCK,
        ]
    )
    config = WatcherConfig(
        label_selector="app=x",
        field_selector="metadata.name!=z",
        page_size=1,
        request_timeout=Timeout(5),
        watch_request_timeout=None,
    )
    with anyio.fail_after(5):
        events = await take(watcher(api.as_api(), config), 7)

    assert describe(events) == [
        ("Init",),
        ("InitApply", "a", "1"),
        ("InitApply", "b", "2"),
        ("InitDone",),
        ("Apply", "c", "8"),
        ("Apply", "a", "9"),
        ("Delete", "b", "10"),
    ]
    assert [c["continue_token"] for c in api.list_calls] == [None, "c1"]
    for call in api.list_calls:
        assert call["limit"] == 1
        assert call["label_selector"] == "app=x"
        assert call["field_selector"] == "metadata.name!=z"
        assert call["request_timeout"] is config.request_timeout
        assert call["invalid"] is InvalidObjects.INCLUDE
    [watch] = api.watch_calls
    assert watch["resource_version"] == "7"
    assert watch["timeout_seconds"] == 290
    assert watch["allow_bookmarks"] is True
    assert watch["label_selector"] == "app=x"
    assert watch["field_selector"] == "metadata.name!=z"
    assert watch["request_timeout"] is None
    assert watch["invalid"] is InvalidObjects.INCLUDE


async def test_a_bookmark_moves_the_resume_version() -> None:
    api = FakeApi(ConfigMap)
    api.pages.append(Page([], resource_version="5"))
    # the server ends the first watch right after a bookmark
    api.watches.append([bookmark("12")])
    with anyio.fail_after(5):
        events = await run_until(
            watcher(api.as_api()), lambda: len(api.watch_calls) >= 2
        )
    assert describe(events) == [("Init",), ("InitDone",), ("Bookmark", "12")]
    assert [c["resource_version"] for c in api.watch_calls] == ["5", "12"]
    assert len(api.list_calls) == 1


async def test_init_done_carries_the_version_of_the_list() -> None:
    api = FakeApi(ConfigMap)
    api.pages.extend(
        [
            Page([cm("a", "1")], continue_="c1", resource_version="6"),
            Page([cm("b", "2")], resource_version="7"),
        ]
    )
    with anyio.fail_after(5):
        events = await take(watcher(api.as_api()), 4)
    assert events[3] == InitDone("7")


async def test_a_bookmark_without_a_version_sends_nothing() -> None:
    api = FakeApi(ConfigMap)
    api.pages.append(Page([], resource_version="5"))
    api.watches.append([bookmark(""), event("ADDED", cm("a", "6")), BLOCK])
    with anyio.fail_after(5):
        events = await take(watcher(api.as_api()), 3)
    assert describe(events) == [("Init",), ("InitDone",), ("Apply", "a", "6")]


async def test_a_watch_the_server_ends_is_reopened_without_listing() -> None:
    api = FakeApi(ConfigMap)
    api.pages.append(Page([cm("a", "1")], resource_version="5"))
    api.watches.append([event("ADDED", cm("b", "6"))])
    backoff = RecordingBackoff()
    with anyio.fail_after(5):
        await run_until(
            watcher(api.as_api(), backoff=backoff), lambda: len(api.watch_calls) >= 2
        )
    assert [c["resource_version"] for c in api.watch_calls] == ["5", "6"]
    assert len(api.list_calls) == 1
    assert backoff.next_calls == 0


async def test_gone_mid_watch_relists_without_backing_off() -> None:
    api = FakeApi(ConfigMap)
    api.pages.extend(
        [
            Page([cm("a", "1")], resource_version="5"),
            Page([cm("a", "9")], resource_version="9"),
        ]
    )
    api.watches.append([event("MODIFIED", cm("a", "6")), build_exception(410, "gone")])
    backoff = RecordingBackoff()
    errors: list[Exception] = []
    with anyio.fail_after(5):
        events = await run_until(
            watcher(api.as_api(), backoff=backoff, on_error=errors.append),
            lambda: len(api.watch_calls) >= 2,
        )
    assert describe(events) == [
        ("Init",),
        ("InitApply", "a", "1"),
        ("InitDone",),
        ("Apply", "a", "6"),
        ("Init",),
        ("InitApply", "a", "9"),
        ("InitDone",),
    ]
    assert [c["resource_version"] for c in api.watch_calls] == ["5", "9"]
    assert errors == []
    assert backoff.next_calls == 0


async def test_other_errors_back_off_and_report_recovery() -> None:
    api = FakeApi(ConfigMap)
    api.pages.append(Page([], resource_version="5"))
    api.watches.extend(
        [[build_exception(500, "boom")], [event("ADDED", cm("b", "7")), BLOCK]]
    )
    backoff = RecordingBackoff()
    errors: list[Exception] = []
    recovered: list[None] = []
    with anyio.fail_after(5):
        events = await run_until(
            watcher(
                api.as_api(),
                backoff=backoff,
                on_error=errors.append,
                on_recovered=lambda: recovered.append(None),
            ),
            lambda: bool(recovered),
        )
    assert describe(events)[-1] == ("Apply", "b", "7")
    assert backoff.next_calls == 1
    assert [type(e) for e in errors] == [KubernetesError]
    assert recovered == [None]
    # the failed watch is retried from the same version, without listing
    assert [c["resource_version"] for c in api.watch_calls] == ["5", "5"]
    assert len(api.list_calls) == 1


async def test_a_failed_list_is_retried_from_the_start() -> None:
    api = FakeApi(ConfigMap)
    api.pages.extend(
        [
            Page([cm("a", "1")], continue_="c1"),
            build_exception(500, "boom"),
            Page([cm("a", "1")], continue_="c2"),
            Page([cm("b", "2")], resource_version="3"),
        ]
    )
    backoff = RecordingBackoff()
    with anyio.fail_after(5):
        events = await take(watcher(api.as_api(), backoff=backoff), 6)
    assert describe(events) == [
        ("Init",),
        ("InitApply", "a", "1"),
        ("Init",),
        ("InitApply", "a", "1"),
        ("InitApply", "b", "2"),
        ("InitDone",),
    ]
    assert [c["continue_token"] for c in api.list_calls] == [None, "c1", None, "c2"]
    assert backoff.next_calls == 1


async def test_a_list_failing_past_its_first_page_still_gives_up() -> None:
    # the first page succeeding is no recovery: the list as a whole failed
    api = FakeApi(ConfigMap)
    api.pages.extend(
        [
            Page([cm("a", "1")], continue_="c1"),
            build_exception(500, "one"),
            Page([cm("a", "1")], continue_="c1"),
            build_exception(500, "two"),
        ]
    )
    backoff = RecordingBackoff(max_retries=1)
    errors: list[Exception] = []
    recovered: list[None] = []
    stream = watcher(
        api.as_api(),
        backoff=backoff,
        on_error=errors.append,
        on_recovered=lambda: recovered.append(None),
    )
    with anyio.fail_after(5), pytest.raises(KubernetesError) as raised:
        await take(stream, 100)
    assert raised.value is errors[-1]
    assert len(errors) == 2
    assert backoff.resets == 1  # when the stream started, not since
    assert recovered == []


async def test_a_watcher_starts_its_backoff_over() -> None:
    # a backoff that gave up in an earlier watcher
    backoff = RecordingBackoff(max_retries=1)
    backoff.attempts = 1
    api = FakeApi(ConfigMap)
    api.pages.extend(
        [build_exception(500, "boom"), Page([cm("a", "1")], resource_version="1")]
    )
    with anyio.fail_after(5):
        events = await take(watcher(api.as_api(), backoff=backoff), 4)
    # the failed list sent its Init before failing; the retry lists again
    assert describe(events) == [
        ("Init",),
        ("Init",),
        ("InitApply", "a", "1"),
        ("InitDone",),
    ]
    assert backoff.next_calls == 1


async def test_a_list_that_succeeds_after_failing_reports_recovery_once() -> None:
    api = FakeApi(ConfigMap)
    api.pages.extend(
        [
            build_exception(500, "boom"),
            Page([cm("a", "1")], continue_="c1"),
            Page([cm("b", "2")], resource_version="3"),
        ]
    )
    backoff = RecordingBackoff()
    recovered: list[None] = []
    with anyio.fail_after(5):
        await take(
            watcher(
                api.as_api(),
                backoff=backoff,
                on_recovered=lambda: recovered.append(None),
            ),
            5,  # Init, Init, a, b, then InitDone, once the whole list succeeded
        )
    assert recovered == [None]
    # when the stream started, then once the whole list succeeded
    assert backoff.resets == 2


async def test_gone_during_the_list_backs_off() -> None:
    # an expired continue token: unlike a 410 mid-watch, it is not re-listed at
    # once, which could loop with no pause if the token keeps expiring
    api = FakeApi(ConfigMap)
    api.pages.extend(
        [
            Page([cm("a", "1")], continue_="c1"),
            build_exception(410, "expired"),
            Page([cm("a", "1")], continue_="c2"),
            Page([cm("b", "2")], resource_version="3"),
        ]
    )
    backoff = RecordingBackoff()
    errors: list[Exception] = []
    with anyio.fail_after(5):
        await take(watcher(api.as_api(), backoff=backoff, on_error=errors.append), 6)
    assert backoff.next_calls == 1
    assert [type(e) for e in errors] == [Gone]
    assert [c["continue_token"] for c in api.list_calls] == [None, "c1", None, "c2"]


async def test_reraises_once_the_backoff_gives_up() -> None:
    api = FakeApi(ConfigMap)
    api.pages.append(Page([], resource_version="5"))
    api.watches.extend([[build_exception(500, "one")], [build_exception(500, "two")]])
    errors: list[Exception] = []
    stream = watcher(
        api.as_api(),
        backoff=ExponentialBackoff(initial=0, jitter=False, max_retries=1),
        on_error=errors.append,
    )
    with anyio.fail_after(5), pytest.raises(KubernetesError) as raised:
        await take(stream, 100)
    assert raised.value is errors[-1]
    assert len(errors) == 2
    assert api.open_watches == 0


async def test_objects_that_do_not_fit_are_logged_and_skipped(
    caplog: pytest.LogCaptureFixture,
) -> None:
    api = FakeApi(ConfigMap)
    bad_listed = invalid_event("bad-listed", "2").object
    api.pages.append(Page([cm("a", "1")], resource_version="5", invalid=[bad_listed]))
    api.watches.append(
        [invalid_event("bad-watched", "8"), event("ADDED", cm("c", "9")), BLOCK]
    )
    backoff = RecordingBackoff()
    with caplog.at_level(logging.ERROR, logger="kubex_runtime.watcher"):
        with anyio.fail_after(5):
            events = await take(watcher(api.as_api(), backoff=backoff), 4)
    assert describe(events) == [
        ("Init",),
        ("InitApply", "a", "1"),
        ("InitDone",),
        ("Apply", "c", "9"),
    ]
    assert backoff.next_calls == 0
    messages = [r.getMessage() for r in caplog.records]
    assert any("ns/bad-listed" in m for m in messages)
    assert any("ns/bad-watched" in m for m in messages)


async def test_an_invalid_object_still_moves_the_resume_version() -> None:
    api = FakeApi(ConfigMap)
    api.pages.append(Page([], resource_version="5"))
    api.watches.append([invalid_event("bad", "8")])
    with anyio.fail_after(5):
        await run_until(watcher(api.as_api()), lambda: len(api.watch_calls) >= 2)
    assert [c["resource_version"] for c in api.watch_calls] == ["5", "8"]


async def test_a_watch_that_stalls_past_its_timeout_is_reopened(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(WATCHER_MODULE, "_STALL_MARGIN", 0.02)
    api = FakeApi(ConfigMap)
    api.pages.append(Page([], resource_version="5"))
    errors: list[Exception] = []
    with anyio.fail_after(5):
        await run_until(
            watcher(
                api.as_api(),
                WatcherConfig(timeout=0),
                backoff=RecordingBackoff(),
                on_error=errors.append,
            ),
            lambda: len(api.watch_calls) >= 2,
        )
    assert isinstance(errors[0], KubexTimeoutError)
    assert [c["resource_version"] for c in api.watch_calls][:2] == ["5", "5"]
    assert api.open_watches == 0


async def test_without_a_timeout_a_quiet_watch_stays_open(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(WATCHER_MODULE, "_STALL_MARGIN", 0.0)
    api = FakeApi(ConfigMap)
    api.pages.append(Page([], resource_version="5"))
    errors: list[Exception] = []
    stream = watcher(api.as_api(), WatcherConfig(timeout=None), on_error=errors.append)
    with anyio.fail_after(5):
        async with anyio.create_task_group() as group:

            async def drain() -> None:
                async for _ in stream:
                    pass

            group.start_soon(drain)
            while api.open_watches != 1:
                await anyio.sleep(0.001)
            await anyio.sleep(0.05)
            group.cancel_scope.cancel()
    assert errors == []
    assert len(api.watch_calls) == 1
    assert api.watch_calls[0]["timeout_seconds"] is None


async def test_closing_the_watcher_closes_the_watch() -> None:
    api = FakeApi(ConfigMap)
    api.pages.append(Page([cm("a", "1")], resource_version="1"))
    api.watches.append([event("ADDED", cm("b", "2")), BLOCK])
    with anyio.fail_after(5):
        events = await take(watcher(api.as_api()), 4)
    assert describe(events)[-1] == ("Apply", "b", "2")
    assert api.open_watches == 0


STREAMING = WatcherConfig(initial_list_strategy=InitialListStrategy.STREAMING_LIST)
WITH_FALLBACK = WatcherConfig(
    initial_list_strategy=InitialListStrategy.STREAMING_LIST_WITH_FALLBACK
)


def initial_end(rv: str) -> Any:
    return bookmark(rv, initial_events_end=True)


def unsupported() -> UnprocessableEntity[Any]:
    error = build_exception(422, "sendInitialEvents is forbidden")
    assert isinstance(error, UnprocessableEntity)
    return error


def test_a_streaming_list_needs_bookmarks() -> None:
    for strategy in (
        InitialListStrategy.STREAMING_LIST,
        InitialListStrategy.STREAMING_LIST_WITH_FALLBACK,
    ):
        with pytest.raises(ValueError, match="bookmarks"):
            WatcherConfig(initial_list_strategy=strategy, bookmarks=False)
    WatcherConfig(bookmarks=False)


async def test_the_default_is_a_streaming_list() -> None:
    api = FakeApi(ConfigMap, watch_list=True)
    api.watches.append([event("ADDED", cm("a", "1")), initial_end("5"), BLOCK])
    with anyio.fail_after(5):
        events = await take(watcher(api.as_api()), 3)
    assert describe(events) == [("Init",), ("InitApply", "a", "1"), ("InitDone",)]
    assert [c["send_initial_events"] for c in api.watch_calls] == [True]
    assert api.list_calls == []


async def test_the_default_falls_back_to_paged_lists() -> None:
    api = FakeApi(ConfigMap)  # a server without WatchList
    api.pages.append(Page([cm("a", "1")], resource_version="5"))
    errors: list[Exception] = []
    with anyio.fail_after(5):
        events = await run_until(
            watcher(api.as_api(), on_error=errors.append),
            lambda: len(api.watch_calls) >= 1,
        )
    assert describe(events) == [("Init",), ("InitApply", "a", "1"), ("InitDone",)]
    assert len(api.rejected_watch_calls) == 1
    assert [c["send_initial_events"] for c in api.watch_calls] == [None]
    assert [c["resource_version"] for c in api.watch_calls] == ["5"]
    assert errors == []


async def test_without_bookmarks_the_default_is_paged_lists() -> None:
    api = FakeApi(ConfigMap, watch_list=True)
    api.pages.append(Page([], resource_version="5"))
    with anyio.fail_after(5):
        await run_until(
            watcher(api.as_api(), WatcherConfig(bookmarks=False)),
            lambda: len(api.watch_calls) >= 1,
        )
    assert len(api.list_calls) == 1
    assert [c["send_initial_events"] for c in api.watch_calls] == [None]
    assert [c["allow_bookmarks"] for c in api.watch_calls] == [False]


async def test_a_streaming_list_starts_the_watch_with_the_current_objects() -> None:
    api = FakeApi(ConfigMap, watch_list=True)
    api.watches.append(
        [
            event("ADDED", cm("a", "1")),
            bookmark("2"),  # a checkpoint, not the end of the initial events
            event("ADDED", cm("b", "3")),
            initial_end("5"),
            event("MODIFIED", cm("a", "6")),
            event("DELETED", cm("b", "7")),
        ]
    )
    with anyio.fail_after(5):
        events = await run_until(
            watcher(api.as_api(), STREAMING), lambda: len(api.watch_calls) >= 2
        )
    assert describe(events) == [
        ("Init",),
        ("InitApply", "a", "1"),
        ("InitApply", "b", "3"),
        ("InitDone",),
        ("Apply", "a", "6"),
        ("Delete", "b", "7"),
    ]
    assert api.list_calls == []
    first, second = api.watch_calls
    assert first["send_initial_events"] is True
    assert first["resource_version"] is None
    assert first["allow_bookmarks"] is True
    assert first["invalid"] is InvalidObjects.INCLUDE
    # the stream the server ended is reopened as a plain watch
    assert second["send_initial_events"] is None
    assert second["resource_version"] == "7"


async def test_an_empty_streaming_list() -> None:
    api = FakeApi(ConfigMap, watch_list=True)
    api.watches.append([initial_end("5"), event("ADDED", cm("a", "6")), BLOCK])
    with anyio.fail_after(5):
        events = await take(watcher(api.as_api(), STREAMING), 3)
    assert describe(events) == [("Init",), ("InitDone",), ("Apply", "a", "6")]


async def test_a_streaming_list_ends_with_the_version_of_its_last_bookmark() -> None:
    api = FakeApi(ConfigMap, watch_list=True)
    api.watches.append(
        [event("ADDED", cm("a", "1")), initial_end("5"), bookmark("8"), BLOCK]
    )
    with anyio.fail_after(5):
        events = await take(watcher(api.as_api(), STREAMING), 4)
    assert events[2:] == [InitDone("5"), Bookmark("8")]


async def test_objects_that_do_not_fit_are_skipped_in_a_streaming_list(
    caplog: pytest.LogCaptureFixture,
) -> None:
    api = FakeApi(ConfigMap, watch_list=True)
    api.watches.append(
        [invalid_event("bad", "2"), event("ADDED", cm("a", "3")), initial_end("4")]
    )
    with caplog.at_level(logging.ERROR, logger="kubex_runtime.watcher"):
        with anyio.fail_after(5):
            events = await take(watcher(api.as_api(), STREAMING), 3)
    assert describe(events) == [("Init",), ("InitApply", "a", "3"), ("InitDone",)]
    assert any("ns/bad" in r.getMessage() for r in caplog.records)


async def test_gone_after_a_streaming_list_streams_again_without_backing_off() -> None:
    api = FakeApi(ConfigMap, watch_list=True)
    api.watches.extend(
        [
            [initial_end("5"), build_exception(410, "gone")],
            [event("ADDED", cm("a", "9")), initial_end("9"), BLOCK],
        ]
    )
    backoff = RecordingBackoff()
    with anyio.fail_after(5):
        events = await take(watcher(api.as_api(), STREAMING, backoff=backoff), 5)
    assert describe(events) == [
        ("Init",),
        ("InitDone",),
        ("Init",),
        ("InitApply", "a", "9"),
        ("InitDone",),
    ]
    assert [c["send_initial_events"] for c in api.watch_calls] == [True, True]
    assert [c["resource_version"] for c in api.watch_calls] == [None, None]
    assert backoff.next_calls == 0


async def test_a_streaming_list_cut_short_is_retried_after_the_backoff() -> None:
    # the stream ends, or fails, before the bookmark that ends the initial
    # events: the objects so far are no complete list, so no recovery yet
    api = FakeApi(ConfigMap, watch_list=True)
    api.watches.extend(
        [
            [build_exception(500, "boom")],
            [event("ADDED", cm("a", "1"))],
            [event("ADDED", cm("a", "1")), build_exception(410, "gone")],
            [event("ADDED", cm("a", "1")), initial_end("2"), BLOCK],
        ]
    )
    backoff = RecordingBackoff()
    errors: list[Exception] = []
    recovered: list[None] = []
    with anyio.fail_after(5):
        events = await run_until(
            watcher(
                api.as_api(),
                STREAMING,
                backoff=backoff,
                on_error=errors.append,
                on_recovered=lambda: recovered.append(None),
            ),
            lambda: bool(recovered),
        )
    # the first watch fails before the server sends anything: no Init for it
    assert describe(events) == [
        ("Init",),
        ("InitApply", "a", "1"),
        ("Init",),
        ("InitApply", "a", "1"),
        ("Init",),
        ("InitApply", "a", "1"),
        ("InitDone",),
    ]
    assert [type(e) for e in errors] == [KubernetesError, KubexClientException, Gone]
    assert "initial events" in str(errors[1])
    assert backoff.next_calls == 3
    # when the stream started, then once the initial events ended
    assert backoff.resets == 2
    assert recovered == [None]
    assert all(c["send_initial_events"] is True for c in api.watch_calls)
    assert api.list_calls == []


async def test_a_rejected_streaming_list_is_retried_without_a_fallback() -> None:
    api = FakeApi(ConfigMap, watch_list=True)
    api.watches.extend([[unsupported()], [initial_end("5"), BLOCK]])
    backoff = RecordingBackoff()
    errors: list[Exception] = []
    with anyio.fail_after(5):
        events = await take(
            watcher(api.as_api(), STREAMING, backoff=backoff, on_error=errors.append),
            2,
        )
    assert describe(events) == [("Init",), ("InitDone",)]
    assert [type(e) for e in errors] == [UnprocessableEntity]
    assert backoff.next_calls == 1
    assert api.list_calls == []


async def test_a_rejected_streaming_list_falls_back_to_listing_for_good(
    caplog: pytest.LogCaptureFixture,
) -> None:
    api = FakeApi(ConfigMap, watch_list=True)
    api.pages.extend(
        [
            Page([cm("a", "1")], resource_version="5"),
            Page([cm("a", "9")], resource_version="9"),
        ]
    )
    api.watches.extend(
        [[unsupported()], [event("ADDED", cm("b", "6")), build_exception(410, "gone")]]
    )
    backoff = RecordingBackoff()
    errors: list[Exception] = []
    with caplog.at_level(logging.INFO, logger="kubex_runtime.watcher"):
        with anyio.fail_after(5):
            events = await run_until(
                watcher(
                    api.as_api(),
                    WITH_FALLBACK,
                    backoff=backoff,
                    on_error=errors.append,
                ),
                lambda: len(api.watch_calls) >= 3,
            )
    # no Init for the rejected streaming list
    assert describe(events) == [
        ("Init",),
        ("InitApply", "a", "1"),
        ("InitDone",),
        ("Apply", "b", "6"),
        ("Init",),
        ("InitApply", "a", "9"),
        ("InitDone",),
    ]
    # after the fallback, a 410 re-lists with list requests, not a streaming list
    assert [c["send_initial_events"] for c in api.watch_calls] == [True, None, None]
    assert [c["resource_version"] for c in api.watch_calls] == [None, "5", "9"]
    assert len(api.list_calls) == 2
    assert errors == []
    assert backoff.next_calls == 0
    assert any("paged lists" in r.getMessage() for r in caplog.records)


async def test_a_streaming_list_the_server_ends_early_falls_back_for_good(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # a stream that fails is retried as a streaming list; one the server ends
    # before the bookmark that ends the initial events comes from a server
    # that ignores sendInitialEvents
    api = FakeApi(ConfigMap, watch_list=True)
    api.pages.extend(
        [
            Page([cm("a", "1")], resource_version="5"),
            Page([cm("a", "9")], resource_version="9"),
        ]
    )
    api.watches.extend(
        [
            [event("ADDED", cm("a", "1")), build_exception(500, "boom")],
            [event("ADDED", cm("a", "1"))],
            [build_exception(410, "gone")],
        ]
    )
    backoff = RecordingBackoff()
    errors: list[Exception] = []
    with caplog.at_level(logging.WARNING, logger="kubex_runtime.watcher"):
        with anyio.fail_after(5):
            events = await run_until(
                watcher(
                    api.as_api(),
                    WITH_FALLBACK,
                    backoff=backoff,
                    on_error=errors.append,
                ),
                lambda: len(api.watch_calls) >= 4,
            )
    assert describe(events) == [
        ("Init",),
        ("InitApply", "a", "1"),
        ("Init",),
        ("InitApply", "a", "1"),
        ("Init",),
        ("InitApply", "a", "1"),
        ("InitDone",),
        ("Init",),
        ("InitApply", "a", "9"),
        ("InitDone",),
    ]
    # after the fallback, a 410 re-lists with list requests, not a streaming list
    assert [c["send_initial_events"] for c in api.watch_calls] == [
        True,
        True,
        None,
        None,
    ]
    assert len(api.list_calls) == 2
    assert [type(e) for e in errors] == [KubernetesError]
    assert backoff.next_calls == 1
    assert any("sendInitialEvents" in r.getMessage() for r in caplog.records)


async def test_a_streaming_list_the_server_takes_does_not_fall_back() -> None:
    api = FakeApi(ConfigMap, watch_list=True)
    api.watches.extend(
        [
            [initial_end("5"), build_exception(410, "gone")],
            [initial_end("9"), BLOCK],
        ]
    )
    with anyio.fail_after(5):
        await run_until(
            watcher(api.as_api(), WITH_FALLBACK), lambda: len(api.watch_calls) >= 2
        )
    assert [c["send_initial_events"] for c in api.watch_calls] == [True, True]
    assert api.list_calls == []


async def test_a_422_after_the_fallback_backs_off() -> None:
    # the list and watch that replace the streaming list do not fall back again
    api = FakeApi(ConfigMap, watch_list=True)
    api.pages.extend([unsupported(), Page([], resource_version="5")])
    api.watches.extend([[unsupported()], [unsupported()], [BLOCK]])
    backoff = RecordingBackoff()
    errors: list[Exception] = []
    with anyio.fail_after(5):
        await run_until(
            watcher(
                api.as_api(), WITH_FALLBACK, backoff=backoff, on_error=errors.append
            ),
            # the watches that fail are open for a moment too
            lambda: len(api.watch_calls) == 3 and api.open_watches == 1,
        )
    assert [type(e) for e in errors] == [UnprocessableEntity, UnprocessableEntity]
    assert backoff.next_calls == 2
    assert [c["send_initial_events"] for c in api.watch_calls] == [True, None, None]
