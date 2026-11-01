"""``finalizer()``: the JSON patches it sends and when it calls ``reconcile``."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import anyio
import pytest

from kubex.core.exceptions import NotFound, UnprocessableEntity
from kubex.core.patch import JsonPatch
from kubex.k8s.v1_35.core.v1.config_map import ConfigMap
from kubex_core.models.metadata import ObjectMetadata
from kubex_core.models.status import Status, StatusDetails
from kubex_runtime import (
    Action,
    FinalizerApply,
    FinalizerCleanup,
    FinalizerError,
    FinalizerEvent,
    finalizer,
)

from ._fakes import cm

pytestmark = pytest.mark.anyio

NAME = "example.com/cleanup"
DELETED_AT = datetime(2026, 1, 1, tzinfo=timezone.utc)


def not_found(details: StatusDetails | None) -> NotFound[Status]:
    return NotFound(Status(code=404, reason="NotFound", details=details))


# what the API server sends for an object that is not there
GONE = StatusDetails(name="a", kind="configmaps")


class FakePatchApi:
    def __init__(self, error: Exception | None = None) -> None:
        self.patches: list[tuple[str, list[dict[str, Any]], Any]] = []
        self._error = error

    async def patch(self, name: str, patch: JsonPatch, *, namespace: Any) -> Any:
        self.patches.append((name, patch.model_dump(mode="json"), namespace))
        if self._error is not None:
            raise self._error
        return None


class Recorder:
    def __init__(self, action: Action | None = None, error: Exception | None = None):
        self.events: list[FinalizerEvent[ConfigMap]] = []
        self._action = action or Action.requeue(60)
        self._error = error

    async def __call__(self, event: FinalizerEvent[ConfigMap]) -> Action:
        self.events.append(event)
        if self._error is not None:
            raise self._error
        return self._action


async def test_adds_the_finalizer_when_there_is_none() -> None:
    api = FakePatchApi()
    reconcile = Recorder()
    with anyio.fail_after(5):
        action = await finalizer(api, NAME, cm("a"), reconcile)
    assert action == Action.await_change()
    assert reconcile.events == []
    assert api.patches == [
        (
            "a",
            [
                {"op": "test", "path": "/metadata/finalizers", "value": None},
                {"op": "add", "path": "/metadata/finalizers", "value": [NAME]},
            ],
            "ns",
        )
    ]


async def test_appends_to_other_finalizers_testing_the_whole_list() -> None:
    api = FakePatchApi()
    reconcile = Recorder()
    obj = cm("a", finalizers=["other/one", "other/two"], uid="uid-a")
    with anyio.fail_after(5):
        action = await finalizer(api, NAME, obj, reconcile)
    assert action == Action.await_change()
    assert reconcile.events == []
    assert api.patches == [
        (
            "a",
            [
                {"op": "test", "path": "/metadata/uid", "value": "uid-a"},
                {
                    "op": "test",
                    "path": "/metadata/finalizers",
                    "value": ["other/one", "other/two"],
                },
                {"op": "add", "path": "/metadata/finalizers/-", "value": NAME},
            ],
            "ns",
        )
    ]


async def test_applies_while_the_object_lives() -> None:
    api = FakePatchApi()
    reconcile = Recorder(Action.requeue(30))
    obj = cm("a", finalizers=[NAME])
    with anyio.fail_after(5):
        action = await finalizer(api, NAME, obj, reconcile)
    assert action == Action.requeue(30)
    assert reconcile.events == [FinalizerApply(obj)]
    assert api.patches == []


async def test_cleans_up_then_removes_the_finalizer_at_its_index() -> None:
    api = FakePatchApi()
    reconcile = Recorder(Action.await_change())
    obj = cm(
        "a",
        finalizers=["other/one", NAME],
        deletion_timestamp=DELETED_AT,
        uid="uid-a",
    )
    with anyio.fail_after(5):
        action = await finalizer(api, NAME, obj, reconcile)
    assert action == Action.await_change()
    assert reconcile.events == [FinalizerCleanup(obj)]
    assert api.patches == [
        (
            "a",
            [
                # not the finalizer of another object recreated under this name
                {"op": "test", "path": "/metadata/uid", "value": "uid-a"},
                {"op": "test", "path": "/metadata/finalizers/1", "value": NAME},
                {"op": "remove", "path": "/metadata/finalizers/1"},
            ],
            "ns",
        )
    ]


async def test_removes_without_a_uid_test_when_the_object_has_none() -> None:
    api = FakePatchApi()
    reconcile = Recorder(Action.await_change())
    obj = cm("a", finalizers=[NAME], deletion_timestamp=DELETED_AT)
    with anyio.fail_after(5):
        await finalizer(api, NAME, obj, reconcile)
    assert api.patches == [
        (
            "a",
            [
                {"op": "test", "path": "/metadata/finalizers/0", "value": NAME},
                {"op": "remove", "path": "/metadata/finalizers/0"},
            ],
            "ns",
        )
    ]


async def test_does_nothing_for_a_deleted_object_without_the_finalizer() -> None:
    api = FakePatchApi()
    reconcile = Recorder()
    obj = cm("a", finalizers=["other/one"], deletion_timestamp=DELETED_AT)
    with anyio.fail_after(5):
        action = await finalizer(api, NAME, obj, reconcile)
    assert action == Action.await_change()
    assert reconcile.events == []
    assert api.patches == []


async def test_a_failed_cleanup_keeps_the_finalizer() -> None:
    api = FakePatchApi()
    reconcile = Recorder(error=RuntimeError("still holding"))
    obj = cm("a", finalizers=[NAME], deletion_timestamp=DELETED_AT)
    with anyio.fail_after(5), pytest.raises(RuntimeError, match="still holding"):
        await finalizer(api, NAME, obj, reconcile)
    assert reconcile.events == [FinalizerCleanup(obj)]
    assert api.patches == []


@pytest.mark.parametrize(
    "details",
    [GONE, StatusDetails(name="a")],
    ids=["named-with-kind", "named-without-kind"],
)
async def test_adding_to_an_object_already_gone_waits_for_the_change(
    details: StatusDetails,
) -> None:
    # the cache has not seen the delete yet: Apply never ran, no cleanup is owed
    api = FakePatchApi(error=not_found(details))
    reconcile = Recorder()
    with anyio.fail_after(5):
        action = await finalizer(api, NAME, cm("a", uid="uid-a"), reconcile)
    assert action == Action.await_change()
    assert reconcile.events == []
    assert len(api.patches) == 1


async def test_removing_from_an_object_already_gone_returns_its_action() -> None:
    api = FakePatchApi(error=not_found(GONE))
    reconcile = Recorder(Action.requeue(30))
    obj = cm("a", finalizers=[NAME], deletion_timestamp=DELETED_AT, uid="uid-a")
    with anyio.fail_after(5):
        action = await finalizer(api, NAME, obj, reconcile)
    assert action == Action.requeue(30)
    assert reconcile.events == [FinalizerCleanup(obj)]
    assert len(api.patches) == 1


@pytest.mark.parametrize(
    "error",
    [
        NotFound("404 page not found"),
        not_found(None),
        # a path the server does not serve, e.g. a wrong group or version
        not_found(StatusDetails()),
        not_found(StatusDetails(name="b", kind="configmaps")),
        # an `api` for another kind
        not_found(StatusDetails(name="a", kind="secrets")),
    ],
    ids=["text-body", "no-details", "no-name", "other-name", "other-kind"],
)
@pytest.mark.parametrize("deleting", [False, True], ids=["add", "remove"])
async def test_a_404_not_naming_the_object_is_raised(
    error: NotFound[Any], deleting: bool
) -> None:
    api = FakePatchApi(error=error)
    reconcile = Recorder()
    if deleting:
        obj = cm("a", finalizers=[NAME], deletion_timestamp=DELETED_AT, uid="uid-a")
    else:
        obj = cm("a", uid="uid-a")
    with anyio.fail_after(5), pytest.raises(NotFound) as raised:
        await finalizer(api, NAME, obj, reconcile)
    assert raised.value is error
    assert len(api.patches) == 1


async def test_a_conflicting_patch_still_raises() -> None:
    # 422: the finalizer list changed meanwhile; the error policy retries
    api = FakePatchApi(error=UnprocessableEntity(content="test failed"))
    reconcile = Recorder()
    obj = cm("a", finalizers=["other/one"], uid="uid-a")
    with anyio.fail_after(5), pytest.raises(UnprocessableEntity):
        await finalizer(api, NAME, obj, reconcile)
    assert reconcile.events == []


async def test_a_nameless_object_is_refused() -> None:
    api = FakePatchApi()
    reconcile = Recorder()
    obj = ConfigMap(metadata=ObjectMetadata(namespace="ns"))
    with anyio.fail_after(5), pytest.raises(FinalizerError):
        await finalizer(api, NAME, obj, reconcile)
    assert reconcile.events == []
    assert api.patches == []
