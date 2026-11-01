"""Watcher-stream adapters and predicates, and that adapters close their upstream."""

from __future__ import annotations

import importlib
from collections.abc import AsyncIterable, AsyncIterator, Callable, Hashable
from typing import Any, TypeVar

import anyio
import anyio.lowlevel
import pytest

from kubex.k8s.v1_35.core.v1.config_map import ConfigMap
from kubex_runtime import (
    Apply,
    Bookmark,
    Delete,
    Event,
    Init,
    InitApply,
    InitDone,
    applied_objects,
    generation,
    predicate_filter,
    resource_version,
    touched_objects,
)
from test.test_runtime._fakes import cm

pytestmark = pytest.mark.anyio

# the module itself, to replace its clock
STREAMS_MODULE = importlib.import_module("kubex_runtime.streams")

T = TypeVar("T")

_TIMEOUT = 5


class _Source:
    """A stream of `items` that records whether it was closed; with `then_wait`
    it stays open after the last item."""

    def __init__(self, items: list[Any], *, then_wait: bool = False) -> None:
        self.items = items
        self.then_wait = then_wait
        self.closed = False

    async def stream(self) -> AsyncIterator[Any]:
        try:
            for item in self.items:
                await anyio.lowlevel.checkpoint()
                yield item
            if self.then_wait:
                await anyio.sleep_forever()
        finally:
            self.closed = True


class _Unclosable:
    """An async iterable without `aclose()`."""

    def __init__(self, items: list[Any]) -> None:
        self._items = iter(items)

    def __aiter__(self) -> _Unclosable:
        return self

    async def __anext__(self) -> Any:
        try:
            return next(self._items)
        except StopIteration:
            raise StopAsyncIteration from None


async def _collect(stream: AsyncIterable[T]) -> list[T]:
    with anyio.fail_after(_TIMEOUT):
        return [item async for item in stream]


def _names(objects: list[ConfigMap]) -> list[tuple[str | None, str | None]]:
    return [(obj.metadata.name, obj.metadata.resource_version) for obj in objects]


def _events() -> list[Event[ConfigMap]]:
    return [
        Init(),
        InitApply(cm("listed")),
        InitDone(),
        Apply(cm("applied")),
        Bookmark("2"),
        Delete(cm("deleted")),
    ]


async def test_applied_objects() -> None:
    objects = await _collect(applied_objects(_Source(_events()).stream()))
    assert _names(objects) == [("listed", "1"), ("applied", "1")]


async def test_touched_objects() -> None:
    objects = await _collect(touched_objects(_Source(_events()).stream()))
    assert _names(objects) == [("listed", "1"), ("applied", "1"), ("deleted", "1")]


async def test_adapters_accept_streams_without_aclose() -> None:
    objects = await _collect(applied_objects(_Unclosable(_events())))
    assert _names(objects) == [("listed", "1"), ("applied", "1")]
    filtered = await _collect(
        predicate_filter(_Unclosable([cm("a", "1")]), resource_version)
    )
    assert _names(filtered) == [("a", "1")]


def test_generation() -> None:
    assert generation(cm("a")) is None
    assert generation(cm("a", uid="u1", generation=3)) == ("u1", 3)


def test_resource_version() -> None:
    assert resource_version(cm("a", "7")) == "7"
    assert resource_version(cm("a", None)) is None  # type: ignore[arg-type]


async def test_predicate_filter_by_generation() -> None:
    objects = [
        cm("a", "1", uid="u", generation=1),
        cm("a", "2", uid="u", generation=1),  # status change: dropped
        cm("a", "3", uid="u", generation=2),
        cm("a", "4", uid="u", generation=2),  # dropped
        cm("a", "5", uid="recreated", generation=2),  # new object, same name
    ]
    filtered = await _collect(predicate_filter(_Source(objects).stream(), generation))
    assert _names(filtered) == [("a", "1"), ("a", "3"), ("a", "5")]


async def test_predicate_filter_by_resource_version() -> None:
    objects = [cm("a", "1"), cm("a", "1"), cm("a", "2"), cm("a", "1")]
    filtered = await _collect(
        predicate_filter(_Source(objects).stream(), resource_version)
    )
    assert _names(filtered) == [("a", "1"), ("a", "2"), ("a", "1")]


async def test_predicate_filter_keeps_one_value_per_object() -> None:
    objects = [
        cm("a", "1"),
        cm("b", "1"),  # same value, other object
        cm("a", "1", namespace="other"),  # same name, other namespace
        cm("b", "1"),  # dropped
    ]
    filtered = await _collect(
        predicate_filter(_Source(objects).stream(), resource_version)
    )
    assert [(obj.metadata.namespace, obj.metadata.name) for obj in filtered] == [
        ("ns", "a"),
        ("ns", "b"),
        ("other", "a"),
    ]


async def test_predicate_filter_passes_objects_without_a_value() -> None:
    objects = [cm("a"), cm("a"), cm("a")]  # no generation
    filtered = await _collect(predicate_filter(_Source(objects).stream(), generation))
    assert len(filtered) == 3


async def test_predicate_filter_without_a_value_keeps_the_last_seen() -> None:
    values: list[Hashable | None] = [1, None, 1, 2]
    objects = [cm("a", str(index)) for index in range(len(values))]

    def predicate(obj: ConfigMap) -> Hashable | None:
        return values[int(obj.metadata.resource_version or "0")]

    filtered = await _collect(predicate_filter(_Source(objects).stream(), predicate))
    # a None value passes and forgets nothing: the next 1 is still a repeat
    assert [obj.metadata.resource_version for obj in filtered] == ["0", "1", "3"]


async def _seen_at(
    sightings: list[tuple[float, ConfigMap]], clock: list[float]
) -> AsyncIterator[ConfigMap]:
    """Yields each object at its time on `clock`."""
    for at, obj in sightings:
        clock[0] = at
        await anyio.lowlevel.checkpoint()
        yield obj


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """The time `predicate_filter` reads, set by `_seen_at`."""
    now = [0.0]
    monkeypatch.setattr(STREAMS_MODULE, "current_time", lambda: now[0])
    return now


async def test_predicate_filter_forgets_values_not_seen_for_ttl(
    clock: list[float],
) -> None:
    sightings = [
        (0.0, cm("a", "1")),
        (5.0, cm("b", "1")),
        (9.0, cm("a", "1")),  # dropped; seen again now
        (18.0, cm("a", "1")),  # seen 9 s ago: dropped
        (20.0, cm("b", "1")),  # not seen for 15 s: forgotten, passes
        (40.0, cm("a", "1")),  # forgotten too
    ]
    filtered = await _collect(
        predicate_filter(_seen_at(sightings, clock), resource_version, ttl=10)
    )
    assert [obj.metadata.name for obj in filtered] == ["a", "b", "b", "a"]


async def test_predicate_filter_forgets_after_an_hour_by_default(
    clock: list[float],
) -> None:
    sightings = [
        (0.0, cm("a", "1")),
        (3599.0, cm("a", "1")),  # dropped
        (7199.0, cm("a", "1")),  # an hour since the last sighting: passes
    ]
    filtered = await _collect(
        predicate_filter(_seen_at(sightings, clock), resource_version)
    )
    assert len(filtered) == 2


async def test_predicate_filter_without_ttl_forgets_nothing(
    clock: list[float],
) -> None:
    sightings = [(0.0, cm("a", "1")), (1e9, cm("a", "1"))]
    filtered = await _collect(
        predicate_filter(_seen_at(sightings, clock), resource_version, ttl=None)
    )
    assert len(filtered) == 1


Adapter = Callable[[AsyncIterator[Any]], AsyncIterator[Any]]

_ADAPTERS: dict[str, Adapter] = {
    "applied_objects": applied_objects,
    "touched_objects": touched_objects,
    "predicate_filter": lambda stream: predicate_filter(stream, resource_version),
}


def _items_for(name: str) -> list[Any]:
    if name == "predicate_filter":
        return [cm("a", "1"), cm("b", "1")]
    return [Apply(cm("a")), Apply(cm("b"))]


@pytest.mark.parametrize("name", list(_ADAPTERS))
async def test_adapter_closes_its_upstream_when_closed(name: str) -> None:
    source = _Source(_items_for(name), then_wait=True)
    adapted = _ADAPTERS[name](source.stream())
    with anyio.fail_after(_TIMEOUT):
        first = await adapted.__anext__()
        assert first.metadata.name == "a"
        assert not source.closed
        await adapted.aclose()  # type: ignore[attr-defined]
    assert source.closed


@pytest.mark.parametrize("name", list(_ADAPTERS))
async def test_adapter_closes_its_upstream_on_break(name: str) -> None:
    source = _Source(_items_for(name), then_wait=True)
    adapted = _ADAPTERS[name](source.stream())
    with anyio.fail_after(_TIMEOUT):
        async for _ in adapted:
            break
        await adapted.aclose()  # type: ignore[attr-defined]
    assert source.closed


@pytest.mark.parametrize("name", list(_ADAPTERS))
async def test_adapter_closes_its_upstream_when_cancelled(name: str) -> None:
    source = _Source(_items_for(name), then_wait=True)
    seen: list[Any] = []

    async def drain() -> None:
        async for item in _ADAPTERS[name](source.stream()):
            seen.append(item)

    with anyio.fail_after(_TIMEOUT):
        async with anyio.create_task_group() as group:
            group.start_soon(drain)
            while len(seen) < 2:
                await anyio.sleep(0.01)
            group.cancel_scope.cancel()
    assert source.closed


@pytest.mark.parametrize("name", list(_ADAPTERS))
async def test_adapter_closes_its_upstream_when_exhausted(name: str) -> None:
    source = _Source(_items_for(name))
    assert len(await _collect(_ADAPTERS[name](source.stream()))) == 2
    assert source.closed


async def test_chained_adapters_close_the_whole_chain() -> None:
    source = _Source([Apply(cm("a", "1")), Apply(cm("a", "2"))], then_wait=True)
    chain = predicate_filter(applied_objects(source.stream()), resource_version)
    with anyio.fail_after(_TIMEOUT):
        assert (await chain.__anext__()).metadata.resource_version == "1"
        await chain.aclose()  # type: ignore[attr-defined]
    assert source.closed
