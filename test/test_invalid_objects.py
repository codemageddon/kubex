"""Objects that do not fit the model: ``invalid=InvalidObjects.INCLUDE`` on
``Api.watch()``/``Api.list()``, and ``WatchEvent.is_initial_events_end``."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, assert_type

import pytest
from pydantic import ValidationError

from kubex.api import Api
from kubex.core.exceptions import Gone
from kubex.core.invalid_object import InvalidObject, ListWithInvalid
from kubex.core.params import InvalidObjects
from kubex.core.watch_event import (
    EventType,
    InvalidWatchEvent,
    WatchEvent,
    _parse_watch_event,
)
from kubex.k8s.v1_35.core.v1.pod import Pod
from kubex_core.models.list_entity import ListEntity
from test.stub_client import StubClient


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _pod(name: str, rv: str = "1", **extra: Any) -> dict[str, Any]:
    return {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"name": name, "namespace": "default", "resourceVersion": rv},
        **extra,
    }


def _bad_pod(name: str, rv: str = "1") -> dict[str, Any]:
    # `spec.containers` must be a list.
    return _pod(name, rv, spec={"containers": "not-a-list"})


def _event(event_type: str, obj: Any) -> dict[str, Any]:
    return {"type": event_type, "object": obj}


def _bookmark(rv: str, annotations: dict[str, str] | None = None) -> dict[str, Any]:
    metadata: dict[str, Any] = {"resourceVersion": rv}
    if annotations is not None:
        metadata["annotations"] = annotations
    return _event("BOOKMARK", {"kind": "Pod", "apiVersion": "v1", "metadata": metadata})


_END_BOOKMARK = _bookmark("10", {"k8s.io/initial-events-end": "true"})

_GONE = _event(
    "ERROR",
    {
        "apiVersion": "v1",
        "kind": "Status",
        "metadata": {},
        "status": "Failure",
        "code": 410,
        "reason": "Expired",
        "message": "too old resource version",
    },
)


def _lines(*events: dict[str, Any]) -> list[str]:
    return [json.dumps(event) for event in events]


def _list_json(*items: Any, **extra: Any) -> bytes:
    return json.dumps(
        {
            "apiVersion": "v1",
            "kind": "PodList",
            "metadata": {"resourceVersion": "100", "continue": "next-page"},
            "items": list(items),
            **extra,
        }
    ).encode()


# --- Parsing one watch event ---------------------------------------------------


@pytest.mark.parametrize("event_type", ["ADDED", "MODIFIED", "DELETED"])
def test_include_turns_an_invalid_object_into_an_invalid_watch_event(
    event_type: str,
) -> None:
    raw = _bad_pod("bad", rv="7")
    event = _parse_watch_event(Pod, _event(event_type, raw), InvalidObjects.INCLUDE)

    assert isinstance(event, InvalidWatchEvent)
    assert event.type is EventType(event_type)
    assert event.object.raw == raw
    assert event.object.metadata.name == "bad"
    assert event.object.metadata.namespace == "default"
    assert event.object.metadata.resource_version == "7"
    assert isinstance(event.object.error, ValidationError)
    assert "containers" in str(event.object.error)


def test_include_returns_a_watch_event_for_a_valid_object() -> None:
    event = _parse_watch_event(Pod, _event("ADDED", _pod("ok")), InvalidObjects.INCLUDE)
    assert isinstance(event, WatchEvent)
    assert isinstance(event.object, Pod)


def test_raise_keeps_raising_validation_error() -> None:
    with pytest.raises(ValidationError):
        _parse_watch_event(Pod, _event("ADDED", _bad_pod("bad")), InvalidObjects.RAISE)


def test_include_still_raises_for_a_bookmark_that_does_not_parse() -> None:
    bookmark_without_metadata = _event("BOOKMARK", {"kind": "Pod"})
    with pytest.raises(ValidationError):
        _parse_watch_event(Pod, bookmark_without_metadata, InvalidObjects.INCLUDE)


def test_include_still_raises_error_events() -> None:
    with pytest.raises(Gone):
        _parse_watch_event(Pod, _GONE, InvalidObjects.INCLUDE)


@pytest.mark.parametrize(
    "obj",
    [
        pytest.param(None, id="null-object"),
        pytest.param(["not", "an", "object"], id="list-object"),
        pytest.param({"kind": "Pod", "spec": {"containers": 1}}, id="no-metadata"),
        pytest.param(
            {"kind": "Pod", "metadata": {"namespace": "default"}, "spec": 1},
            id="no-name",
        ),
        pytest.param({"kind": "Pod", "metadata": "nope", "spec": 1}, id="bad-metadata"),
    ],
)
def test_include_raises_when_the_object_cannot_be_identified(obj: Any) -> None:
    with pytest.raises(ValidationError):
        _parse_watch_event(Pod, _event("MODIFIED", obj), InvalidObjects.INCLUDE)


def test_invalid_object_repr_is_short() -> None:
    event = _parse_watch_event(
        Pod, _event("ADDED", _bad_pod("bad")), InvalidObjects.INCLUDE
    )
    assert isinstance(event, InvalidWatchEvent)
    assert repr(event.object) == (
        "InvalidObject(kind='Pod', namespace='default', name='bad', errors=1)"
    )


# --- is_initial_events_end -----------------------------------------------------


def test_end_bookmark_is_initial_events_end() -> None:
    assert WatchEvent(Pod, _END_BOOKMARK).is_initial_events_end


@pytest.mark.parametrize(
    "raw_event",
    [
        pytest.param(_bookmark("11"), id="periodic-bookmark"),
        pytest.param(_bookmark("11", {"other": "true"}), id="other-annotation"),
        pytest.param(
            _bookmark("11", {"k8s.io/initial-events-end": "false"}), id="false-value"
        ),
        pytest.param(_event("ADDED", _pod("ok")), id="not-a-bookmark"),
        pytest.param(
            _event(
                "ADDED",
                {
                    **_pod("ok"),
                    "metadata": {
                        "name": "ok",
                        "annotations": {"k8s.io/initial-events-end": "true"},
                    },
                },
            ),
            id="annotated-object",
        ),
    ],
)
def test_other_events_are_not_initial_events_end(raw_event: dict[str, Any]) -> None:
    assert not WatchEvent(Pod, raw_event).is_initial_events_end


def test_invalid_watch_event_is_never_initial_events_end() -> None:
    event = _parse_watch_event(
        Pod, _event("ADDED", _bad_pod("bad")), InvalidObjects.INCLUDE
    )
    assert not event.is_initial_events_end


# --- Api.watch -----------------------------------------------------------------


@pytest.mark.anyio
@pytest.mark.parametrize("invalid", [InvalidObjects.INCLUDE, "include"])
async def test_watch_include_goes_on_after_an_invalid_object(
    invalid: InvalidObjects,
) -> None:
    client = StubClient(
        stream_lines=_lines(
            _event("ADDED", _pod("a", rv="1")),
            _event("MODIFIED", _bad_pod("bad", rv="2")),
            _END_BOOKMARK,
            _event("DELETED", _bad_pod("bad", rv="11")),
            _event("ADDED", _pod("b", rv="12")),
        )
    )
    api: Api[Pod] = Api(Pod, client=client, namespace="default")

    events = [event async for event in api.watch(invalid=invalid)]

    assert [
        (type(e).__name__, e.type, e.object.metadata.resource_version) for e in events
    ] == [
        ("WatchEvent", EventType.ADDED, "1"),
        ("InvalidWatchEvent", EventType.MODIFIED, "2"),
        ("WatchEvent", EventType.BOOKMARK, "10"),
        ("InvalidWatchEvent", EventType.DELETED, "11"),
        ("WatchEvent", EventType.ADDED, "12"),
    ]
    assert [e.is_initial_events_end for e in events] == [
        False,
        False,
        True,
        False,
        False,
    ]


@pytest.mark.anyio
async def test_watch_raises_on_an_invalid_object_by_default() -> None:
    client = StubClient(
        stream_lines=_lines(
            _event("ADDED", _pod("a")),
            _event("MODIFIED", _bad_pod("bad")),
            _event("ADDED", _pod("b")),
        )
    )
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    seen: list[str | None] = []

    with pytest.raises(ValidationError):
        async for event in api.watch():
            seen.append(event.object.metadata.name)

    assert seen == ["a"]


@pytest.mark.anyio
async def test_watch_include_still_raises_on_a_corrupt_line() -> None:
    client = StubClient(stream_lines=['{"type": "ADDED", "object": '])
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    with pytest.raises(json.JSONDecodeError):
        async for _ in api.watch(invalid=InvalidObjects.INCLUDE):
            pass


@pytest.mark.anyio
async def test_watch_rejects_an_unknown_invalid_value() -> None:
    client = StubClient()
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    with pytest.raises(ValueError, match="yield"):
        async for _ in api.watch(invalid="yield"):  # type: ignore[call-overload]
            pass
    assert client.requests == []


# --- Api.list ------------------------------------------------------------------


@pytest.mark.anyio
@pytest.mark.parametrize("invalid", [InvalidObjects.INCLUDE, "include"])
async def test_list_include_keeps_invalid_objects_apart(
    invalid: InvalidObjects,
) -> None:
    bad = _bad_pod("bad", rv="2")
    client = StubClient(response_content=_list_json(_pod("a"), bad, _pod("b")))
    api: Api[Pod] = Api(Pod, client=client, namespace="default")

    result = await api.list(invalid=invalid)

    assert isinstance(result, ListWithInvalid)
    assert isinstance(result, ListEntity)
    assert all(isinstance(item, Pod) for item in result.items)
    assert [item.metadata.name for item in result.items] == ["a", "b"]
    assert len(result.invalid) == 1
    assert isinstance(result.invalid[0], InvalidObject)
    assert result.invalid[0].raw == bad
    assert result.invalid[0].metadata.name == "bad"
    assert result.metadata.resource_version == "100"
    assert result.metadata.continue_ == "next-page"
    assert (result.api_version, result.kind) == ("v1", "PodList")


@pytest.mark.anyio
async def test_list_raises_on_an_invalid_object_by_default() -> None:
    client = StubClient(response_content=_list_json(_pod("a"), _bad_pod("bad")))
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    with pytest.raises(ValidationError):
        await api.list()


@pytest.mark.anyio
async def test_list_include_with_only_valid_objects() -> None:
    client = StubClient(response_content=_list_json(_pod("a"), _pod("b")))
    api: Api[Pod] = Api(Pod, client=client, namespace="default")

    result = await api.list(invalid=InvalidObjects.INCLUDE)

    assert [item.metadata.name for item in result.items] == ["a", "b"]
    assert result.invalid == []


@pytest.mark.anyio
async def test_list_include_with_null_items() -> None:
    content = json.dumps(
        {"apiVersion": "v1", "kind": "PodList", "metadata": {}, "items": None}
    ).encode()
    api: Api[Pod] = Api(Pod, client=StubClient(response_content=content))

    result = await api.list(invalid=InvalidObjects.INCLUDE, namespace="default")

    assert result.items == []
    assert result.invalid == []


@pytest.mark.anyio
@pytest.mark.parametrize(
    "content",
    [
        pytest.param(
            json.dumps(
                {"apiVersion": "v1", "kind": "NotAList", "metadata": {}, "items": []}
            ).encode(),
            id="wrong-kind",
        ),
        pytest.param(
            json.dumps(
                {"apiVersion": "v1", "kind": "PodList", "metadata": {}, "items": {}}
            ).encode(),
            id="items-not-a-list",
        ),
        pytest.param(b"[]", id="not-an-object"),
        pytest.param(
            _list_json({"kind": "Pod", "metadata": {}, "spec": 1}), id="item-no-name"
        ),
    ],
)
async def test_list_include_still_raises_for_a_broken_list(content: bytes) -> None:
    api: Api[Pod] = Api(Pod, client=StubClient(response_content=content))
    with pytest.raises(ValidationError):
        await api.list(invalid=InvalidObjects.INCLUDE, namespace="default")


@pytest.mark.anyio
async def test_list_include_serializes_like_a_list_without_invalid() -> None:
    client = StubClient(
        response_content=_list_json(_pod("a"), _bad_pod("bad"), futureField="kept")
    )
    api: Api[Pod] = Api(Pod, client=client, namespace="default")

    result = await api.list(invalid=InvalidObjects.INCLUDE)
    dumped = result.model_dump(by_alias=True, exclude_none=True, mode="json")

    assert "invalid" not in dumped
    assert dumped["futureField"] == "kept"
    assert dumped["kind"] == "PodList"
    assert [item["metadata"]["name"] for item in dumped["items"]] == ["a"]
    # Items keep their full Pod shape, not just the BaseEntity fields.
    assert dumped["items"][0]["metadata"]["namespace"] == "default"


@pytest.mark.anyio
async def test_list_rejects_an_unknown_invalid_value() -> None:
    client = StubClient()
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    with pytest.raises(ValueError, match="collect"):
        await api.list(invalid="collect")  # type: ignore[call-overload]
    assert client.requests == []


# --- Static types (checked by mypy, never run) ----------------------------------

if TYPE_CHECKING:

    async def _check_types(api: Api[Pod], policy: InvalidObjects) -> None:
        assert_type(await api.list(), ListEntity[Pod])
        assert_type(await api.list(invalid=InvalidObjects.RAISE), ListEntity[Pod])
        assert_type(
            await api.list(invalid=InvalidObjects.INCLUDE), ListWithInvalid[Pod]
        )
        assert_type(await api.list(invalid="include"), ListWithInvalid[Pod])
        assert_type(await api.list(invalid=policy), ListEntity[Pod])

        async for plain in api.watch():
            assert_type(plain, WatchEvent[Pod])
        async for raised in api.watch(invalid="raise"):
            assert_type(raised, WatchEvent[Pod])
        async for included in api.watch(invalid=InvalidObjects.INCLUDE):
            assert_type(included, WatchEvent[Pod] | InvalidWatchEvent)
            # Both kinds of event carry the object's metadata.
            assert_type(included.object.metadata.name, str | None)
        async for dynamic in api.watch(invalid=policy):
            assert_type(dynamic, WatchEvent[Pod] | InvalidWatchEvent)
