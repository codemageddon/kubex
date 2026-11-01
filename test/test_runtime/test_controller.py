"""``Controller``: what triggers a reconcile, how reconciles are scheduled, and how
``running()``/``run()`` end."""

from __future__ import annotations

import importlib
import logging
from collections.abc import AsyncIterable, AsyncIterator, Awaitable, Callable, Iterable
from typing import Any

import anyio
import pytest

from kubex.core.exceptions import (
    KubernetesError,
    KubexConnectionError,
    build_exception,
)
from kubex.k8s.v1_35.core.v1.config_map import ConfigMap
from kubex.k8s.v1_35.core.v1.namespace import Namespace
from kubex_core.models.metadata import ObjectMetadata
from kubex_runtime import (
    Action,
    Apply,
    BoundedBuffer,
    Controller,
    ControllerConfig,
    Delete,
    Event,
    ExponentialBackoff,
    Init,
    InitApply,
    InitDone,
    MergedBuffer,
    ObjectRef,
    ReconcileReason,
    ReconcileResult,
    Store,
    SubscriberBuffer,
    WatcherConfig,
    Writer,
    shared_reflector,
    store,
)
from kubex_runtime.controller import (
    BULK_RECONCILE,
    ERROR_POLICY_REQUESTED_RETRY,
    OBJECT_UPDATED,
    RECONCILER_REQUESTED_RETRY,
    UNKNOWN,
)
from kubex_runtime.controller._triggers import _watched_triggers

from ._fakes import FakeApi, Page, cm, event, owner

pytestmark = pytest.mark.anyio

# the package exports a `watcher` function that hides the module of that name
WATCHER_MODULE = importlib.import_module("kubex_runtime.watcher")

BUFFERS = [
    pytest.param(None, id="default"),
    pytest.param(BoundedBuffer(size=1), id="bounded-1"),
    pytest.param(MergedBuffer(), id="merged"),
]

Reconcile = Callable[[Any, None], Awaitable[Action]]
Policy = Callable[[Any, Exception, None], Action]


def ref(name: str, namespace: str | None = "ns") -> ObjectRef:
    return ObjectRef.of(ConfigMap, name, namespace)


def wait_for_change(obj: Any, error: Exception, ctx: None) -> Action:
    return Action.await_change()


class Recorder:
    """Records (name, resourceVersion) of every reconcile."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def __call__(self, obj: Any, ctx: None) -> Action:
        self.calls.append(
            (obj.metadata.name or "", obj.metadata.resource_version or "")
        )
        return Action.await_change()


async def collect(
    controller: Controller[Any],
    reconcile: Reconcile,
    until: Callable[[list[ReconcileResult]], bool],
    policy: Policy = wait_for_change,
) -> list[ReconcileResult]:
    """The results of `controller` until `until(results)`."""
    results: list[ReconcileResult] = []
    with anyio.fail_after(5):
        async with controller.running(reconcile, policy, None) as stream:
            async for result in stream:
                results.append(result)
                if until(results):
                    break
    return results


async def collect_for(
    controller: Controller[Any],
    reconcile: Reconcile,
    seconds: float,
    policy: Policy = wait_for_change,
) -> list[ReconcileResult]:
    """Every result of `controller` within `seconds`."""
    results: list[ReconcileResult] = []
    with anyio.move_on_after(seconds):
        async with controller.running(reconcile, policy, None) as stream:
            async for result in stream:
                results.append(result)
    return results


async def later(items: Iterable[Any], delay: float = 0.05) -> AsyncIterator[Any]:
    """Yields `items`, `delay` apart, then stays open."""
    for item in items:
        await anyio.sleep(delay)
        yield item
    await anyio.sleep_forever()


@pytest.mark.parametrize("buffer", BUFFERS)
async def test_reconciles_every_object_of_its_watch(
    buffer: SubscriberBuffer | None,
) -> None:
    api = FakeApi(ConfigMap)
    api.pages.append(Page([cm("a", "1"), cm("b", "2")], resource_version="3"))
    api.watches.append([event("MODIFIED", cm("a", "4"))])
    reconcile = Recorder()
    controller = Controller(ConfigMap, api.as_api(), buffer=buffer)

    def done(results: list[ReconcileResult]) -> bool:
        reconciled = {r.obj_ref for r in results}
        return ("a", "4") in reconcile.calls and reconciled >= {ref("a"), ref("b")}

    results = await collect(controller, reconcile, done)
    for result in results:
        assert isinstance(result, ReconcileResult)
        assert result.reason == OBJECT_UPDATED
        assert result.action == Action.await_change()
        assert result.error is None
    assert {r.obj_ref for r in results} == {ref("a"), ref("b")}
    assert controller.store.get(ref("a")) is not None


async def test_nothing_is_reconciled_before_the_store_is_ready() -> None:
    api = FakeApi(ConfigMap)
    api.list_delay = 0.1
    api.pages.append(Page([cm("a", "1")], resource_version="1"))
    ready: list[bool] = []

    async def reconcile(obj: ConfigMap, ctx: None) -> Action:
        ready.append(controller.store.is_ready())
        return Action.await_change()

    controller = Controller(
        ConfigMap, api.as_api(), WatcherConfig(label_selector="app=x")
    ).reconcile_on(later([ref("a")], delay=0))
    # the early trigger is held until the list is applied: run before it, it
    # would find nothing in the store and be dropped, with no result
    results = await collect(
        controller, reconcile, lambda rs: any(r.reason == UNKNOWN for r in rs)
    )
    assert [r.obj_ref for r in results if r.reason == UNKNOWN] == [ref("a")]
    assert ready and all(ready)
    assert api.list_calls[0]["label_selector"] == "app=x"


async def test_waits_for_holds_reconciles_until_its_stores_are_ready() -> None:
    api = FakeApi(ConfigMap)
    api.pages.append(Page([cm("a", "1")], resource_version="1"))
    ready: Store[ConfigMap]
    ready_writer: Writer[ConfigMap]
    ready, ready_writer = store()
    await ready_writer.apply_watcher_event(Init())
    await ready_writer.apply_watcher_event(InitDone())
    late: Store[ConfigMap]
    late_writer: Writer[ConfigMap]
    late, late_writer = store()
    seen_late_ready: list[bool] = []

    async def reconcile(obj: ConfigMap, ctx: None) -> Action:
        seen_late_ready.append(late.is_ready())
        return Action.await_change()

    controller = Controller(ConfigMap, api.as_api()).waits_for(ready, late)
    early: list[ReconcileResult] = []
    with anyio.fail_after(5):
        async with controller.running(reconcile, wait_for_change, None) as results:
            while not controller.store.is_ready():
                await anyio.sleep(0.001)
            # the trigger for "a" is in, but `late` has not listed yet
            with anyio.move_on_after(0.05):
                early.append(await results.receive())
            await late_writer.apply_watcher_event(Init())
            await late_writer.apply_watcher_event(InitDone())
            result = await results.receive()
    assert early == []
    assert result.obj_ref == ref("a")
    assert seen_late_ready == [True]


async def test_a_controller_runs_once() -> None:
    api = FakeApi(ConfigMap)
    api.pages.append(Page([cm("a")], resource_version="1"))
    controller = Controller(ConfigMap, api.as_api())
    await collect(controller, Recorder(), lambda rs: len(rs) >= 1)
    with anyio.fail_after(5), pytest.raises(RuntimeError, match="runs once"):
        async with controller.running(Recorder(), wait_for_change, None):
            pass
    with anyio.fail_after(5), pytest.raises(RuntimeError, match="runs once"):
        await controller.run(Recorder(), wait_for_change, None)


async def test_a_running_controller_cannot_run_again() -> None:
    api = FakeApi(ConfigMap)
    api.pages.append(Page([cm("a")], resource_version="1"))
    controller = Controller(ConfigMap, api.as_api())
    with anyio.fail_after(5):
        async with controller.running(Recorder(), wait_for_change, None) as results:
            with pytest.raises(RuntimeError, match="runs once"):
                async with controller.running(Recorder(), wait_for_change, None):
                    pass
            # the refused run leaves the first one going
            result = await results.receive()
    assert result.obj_ref == ref("a")
    assert result.error is None


@pytest.mark.parametrize("buffer", BUFFERS)
async def test_a_paged_relist_reconciles_new_and_changed_objects(
    buffer: SubscriberBuffer | None,
) -> None:
    """Regression: triggers once came from the raw list, before the store had the
    re-listed objects, so `c` (new, on page 1 of 2) was dropped and `a` was
    reconciled with its old state."""
    api = FakeApi(ConfigMap)
    api.pages.extend(
        [
            Page([cm("a", "1")], resource_version="1"),
            Page([cm("a", "5"), cm("c", "4")], continue_="p2"),
            Page([cm("b", "6")], resource_version="6"),
        ]
    )
    api.watches.append([build_exception(410, "too old resource version")])
    api.list_delay = 0.01
    reconcile = Recorder()
    controller = Controller(ConfigMap, api.as_api(), buffer=buffer)
    wanted = {("a", "5"), ("c", "4"), ("b", "6")}
    await collect(controller, reconcile, lambda _: wanted <= set(reconcile.calls))
    assert reconcile.calls[0] == ("a", "1")
    # nothing was reconciled with the state the re-list replaced
    assert reconcile.calls.count(("a", "1")) == 1


async def test_owns_a_cluster_scoped_owner() -> None:
    """Regression: the owner reference got the dependent's namespace, which a
    cluster-scoped owner is not stored under."""
    namespaces = FakeApi(Namespace)
    namespaces.pages.append(
        Page(
            [Namespace(metadata=ObjectMetadata(name="tenant", resource_version="1"))],
            resource_version="1",
        )
    )
    children = FakeApi(ConfigMap)
    children.list_delay = 0.05
    children.pages.append(
        Page([cm("child", owners=[owner("Namespace", "tenant")])], resource_version="1")
    )
    controller = Controller(Namespace, namespaces.as_api()).owns(
        ConfigMap, children.as_api()
    )
    results = await collect(
        controller,
        Recorder(),
        lambda rs: any(r.reason.related is not None for r in rs),
    )
    related = next(r for r in results if r.reason.related is not None)
    assert related.obj_ref == ObjectRef("core", "Namespace", "tenant", None)
    assert related.reason == ReconcileReason.related_object_updated(ref("child"))


async def test_owns_a_namespaced_owner_through_controller_references_only() -> None:
    parents = FakeApi(ConfigMap)
    parents.pages.append(
        Page(
            [
                cm("parent"),
                cm("parent2"),
                cm("parent3"),
                cm("parent", namespace="other"),
            ],
            resource_version="1",
        )
    )
    children = FakeApi(ConfigMap)
    children.list_delay = 0.05
    children.pages.append(
        Page(
            [
                cm("child-a", owners=[owner("ConfigMap", "parent")]),
                cm("child-b", owners=[owner("ConfigMap", "parent2", controller=False)]),
                cm("child-c", owners=[owner("Secret", "parent3")]),
            ],
            resource_version="1",
        )
    )
    controller = Controller(ConfigMap, parents.as_api()).owns(
        ConfigMap, children.as_api()
    )
    results = await collect_for(controller, Recorder(), 0.3)
    related = [r for r in results if r.reason.related is not None]
    assert [(r.obj_ref, r.reason.related) for r in related] == [
        (ref("parent"), ref("child-a"))
    ]


@pytest.mark.parametrize(
    "relate",
    [
        pytest.param(lambda c, api: c.owns(ConfigMap, api), id="owns"),
        pytest.param(
            lambda c, api: c.watches(ConfigMap, api, lambda obj: [ref("parent")]),
            id="watches",
        ),
    ],
)
async def test_owns_and_watches_trigger_for_a_child_gone_in_a_relist(
    relate: Callable[[Controller[ConfigMap], Any], Controller[ConfigMap]],
) -> None:
    """Regression: a child deleted while its watch was down sends no `Delete`,
    and the re-list that followed dropped it without a trigger, so its owner was
    never reconciled to replace it."""
    parents = FakeApi(ConfigMap)
    parents.pages.append(Page([cm("parent")], resource_version="1"))
    children = FakeApi(ConfigMap)
    children.list_delay = 0.05
    children.pages.append(
        Page([cm("child", owners=[owner("ConfigMap", "parent")])], resource_version="1")
    )
    # the watch resumes from a compacted version: a re-list, without the child
    children.watches.append([build_exception(410, "expired")])
    children.pages.append(Page([], resource_version="2"))
    controller = relate(Controller(ConfigMap, parents.as_api()), children.as_api())
    by_child = ReconcileReason.related_object_updated(ref("child"))
    results = await collect(
        controller,
        Recorder(),
        lambda rs: [r.reason for r in rs].count(by_child) == 2,
    )
    assert [r.obj_ref for r in results if r.reason == by_child] == [ref("parent")] * 2


@pytest.mark.parametrize(
    "relate",
    [
        pytest.param(lambda c, api: c.owns(ConfigMap, api), id="owns"),
        pytest.param(
            lambda c, api: c.watches(ConfigMap, api, lambda obj: [ref("parent")]),
            id="watches",
        ),
    ],
)
async def test_owns_and_watches_trigger_for_a_child_gone_when_a_list_started_over(
    relate: Callable[[Controller[ConfigMap], Any], Controller[ConfigMap]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression: a child found on a list that failed part-way had triggered
    its owner, and the list that started over dropped it without a trigger."""
    monkeypatch.setattr(
        WATCHER_MODULE,
        "default_backoff",
        lambda: ExponentialBackoff(initial=0, jitter=False),
    )
    parents = FakeApi(ConfigMap)
    parents.pages.append(Page([cm("parent")], resource_version="1"))
    children = FakeApi(ConfigMap)
    children.list_delay = 0.05
    children.pages.append(
        Page(
            [cm("child", owners=[owner("ConfigMap", "parent")])],
            continue_="next",
            resource_version="1",
        )
    )
    # the next page fails, and the child is deleted before the list is retried
    children.pages.append(build_exception(500, "boom"))
    children.pages.append(Page([], resource_version="2"))
    controller = relate(Controller(ConfigMap, parents.as_api()), children.as_api())
    by_child = ReconcileReason.related_object_updated(ref("child"))
    results = await collect(
        controller,
        Recorder(),
        lambda rs: [r.reason for r in rs].count(by_child) == 2,
    )
    assert [r.obj_ref for r in results if r.reason == by_child] == [ref("parent")] * 2


CHILD_OF_A = cm("child", uid="1", owners=[owner("ConfigMap", "a")])
CHILD_OF_B = cm("child", uid="1", owners=[owner("ConfigMap", "b")])
# deleted and re-created under its name
NEW_CHILD_OF_B = cm("child", uid="2", owners=[owner("ConfigMap", "b")])
ORPHAN = cm("child", uid="1")


@pytest.mark.parametrize(
    ("events", "owners"),
    [
        pytest.param(
            [Init(), InitApply(CHILD_OF_A), InitDone(), Init(), InitDone()],
            ["a", "a"],
            id="listed-then-gone",
        ),
        pytest.param(
            [Init(), InitDone(), Apply(CHILD_OF_A), Init(), InitDone()],
            ["a", "a"],
            id="applied-then-gone",
        ),
        pytest.param(
            [Init(), InitApply(CHILD_OF_A), InitDone()]
            + [Init(), InitApply(CHILD_OF_A), InitDone()],
            ["a", "a"],
            id="listed-again",
        ),
        pytest.param(
            [Init(), InitApply(CHILD_OF_A), InitDone()]
            + [Init(), InitApply(NEW_CHILD_OF_B), InitDone()],
            ["a", "b", "a"],
            id="re-created-under-its-name",
        ),
        pytest.param(
            [Init(), InitApply(CHILD_OF_A), InitDone(), Delete(CHILD_OF_A)]
            + [Init(), InitDone()],
            ["a", "a"],
            id="deleted",
        ),
        pytest.param(
            [Init(), InitApply(CHILD_OF_A), InitDone(), Apply(CHILD_OF_B)]
            + [Init(), InitDone()],
            ["a", "b", "b"],
            id="owner-changed",
        ),
        pytest.param(
            [Init(), InitApply(CHILD_OF_A), InitDone(), Apply(ORPHAN)]
            + [Init(), InitDone()],
            ["a"],
            id="no-longer-owned",
        ),
        pytest.param(
            # a list that failed part-way starts over, and no longer finds it
            [Init(), InitApply(CHILD_OF_A), Init(), InitDone(), Init(), InitDone()],
            ["a", "a"],
            id="list-started-over",
        ),
        pytest.param(
            [Init(), InitApply(CHILD_OF_A), Init(), InitApply(CHILD_OF_A), InitDone()],
            ["a", "a"],
            id="list-started-over-finds-it-again",
        ),
        pytest.param(
            [Init(), InitApply(CHILD_OF_A), Init(), InitApply(NEW_CHILD_OF_B)]
            + [InitDone()],
            ["a", "b", "a"],
            id="re-created-while-the-list-started-over",
        ),
        pytest.param(
            [Init(), InitApply(CHILD_OF_A), InitDone()]
            + [Init(), InitApply(CHILD_OF_B), Init(), InitDone()],
            ["a", "b", "b"],
            id="owner-changed-before-the-list-started-over",
        ),
    ],
)
async def test_watched_triggers_include_the_objects_a_relist_no_longer_finds(
    events: list[Event[ConfigMap]], owners: list[str]
) -> None:
    async def stream() -> AsyncIterator[Event[ConfigMap]]:
        for item in events:
            yield item

    def mapper(obj: ConfigMap) -> list[ObjectRef]:
        return [ref(o.name) for o in obj.metadata.owner_references or []]

    requests = [r async for r in _watched_triggers(stream(), mapper)]
    assert [r.obj_ref.name for r in requests] == owners
    by_child = ReconcileReason.related_object_updated(ref("child"))
    assert all(r.reason == by_child for r in requests)


async def test_owns_shared_stream_triggers_the_owner_of_a_child_gone_in_a_relist() -> (
    None
):
    parents = FakeApi(ConfigMap)
    parents.pages.append(Page([cm("parent")], resource_version="1"))
    children: Store[ConfigMap]
    child_writer: Writer[ConfigMap]
    children, child_writer = store()
    child = cm("child", owners=[owner("ConfigMap", "parent")])
    seen_children: list[list[str | None]] = []

    async def reconcile(obj: ConfigMap, ctx: None) -> Action:
        seen_children.append([c.metadata.name for c in children.state()])
        return Action.await_change()

    controller = (
        Controller(ConfigMap, parents.as_api())
        .owns_shared_stream(child_writer.subscribe())
        .waits_for(children)
    )
    with anyio.fail_after(5):
        async with controller.running(reconcile, wait_for_change, None) as results:
            await child_writer.apply_watcher_event(Init())
            await child_writer.apply_watcher_event(InitApply(child))
            await child_writer.apply_watcher_event(InitDone())
            # the own trigger and the child's may merge: wait until both are done
            while True:
                with anyio.move_on_after(0.1) as quiet:
                    await results.receive()
                if quiet.cancelled_caught:
                    break
            # a re-list without the child: it was deleted while the watch was down
            await child_writer.apply_watcher_event(Init())
            await child_writer.apply_watcher_event(InitDone())
            after = await results.receive()
    assert seen_children[0] == ["child"]
    assert after.obj_ref == ref("parent")
    assert after.reason == ReconcileReason.related_object_updated(ref("child"))
    # the trigger came once the store had the change
    assert seen_children[-1] == []


async def test_owns_shared_stream_triggers_both_owners_of_a_re_created_child() -> None:
    parents = FakeApi(ConfigMap)
    parents.pages.append(Page([cm("a"), cm("b")], resource_version="1"))
    children: Store[ConfigMap]
    child_writer: Writer[ConfigMap]
    children, child_writer = store()
    await child_writer.apply_watcher_event(Init())
    await child_writer.apply_watcher_event(InitDone())
    subscription = child_writer.subscribe(MergedBuffer())
    # before the controller reads: the child of a is deleted, then re-created
    # under its name for b
    old = cm("child", "1", uid="old", owners=[owner("ConfigMap", "a")])
    await child_writer.apply_watcher_event(Apply(old))
    await child_writer.apply_watcher_event(Delete(old))
    new = cm("child", "2", uid="new", owners=[owner("ConfigMap", "b")])
    await child_writer.apply_watcher_event(Apply(new))
    controller = (
        Controller(ConfigMap, parents.as_api())
        .owns_shared_stream(subscription)
        .waits_for(children)
    )
    results = await collect(
        controller,
        Recorder(),
        lambda results: (
            {r.obj_ref for r in results if r.reason != OBJECT_UPDATED}
            == {ref("a"), ref("b")}
        ),
    )
    related = [r.obj_ref for r in results if r.reason != OBJECT_UPDATED]
    assert sorted(related, key=lambda r: r.name) == [ref("a"), ref("b")]


async def test_for_shared_and_owns_shared_read_and_wait_for_shared_stores() -> None:
    parents_api = FakeApi(ConfigMap)
    parents_api.pages.append(Page([cm("parent")], resource_version="1"))
    children_api = FakeApi(ConfigMap)
    children_api.list_delay = 0.05
    children_api.pages.append(
        Page([cm("child", owners=[owner("ConfigMap", "parent")])], resource_version="1")
    )
    # the watch resumes from a compacted version: a re-list, without the child
    children_api.watches.append([build_exception(410, "expired")])
    children_api.pages.append(Page([], resource_version="2"))
    seen_children: list[list[str | None]] = []
    with anyio.fail_after(5):
        async with (
            shared_reflector(parents_api.as_api()) as parents,
            shared_reflector(children_api.as_api()) as children,
        ):

            async def reconcile(obj: ConfigMap, ctx: None) -> Action:
                seen_children.append([c.metadata.name for c in children.store.state()])
                return Action.await_change()

            controller = Controller.for_shared(ConfigMap, parents).owns_shared(children)
            results = await collect(
                controller,
                reconcile,
                lambda rs: any(r.reason.related is not None for r in rs),
            )
    # held until the children had listed
    assert seen_children[0] == ["child"]
    related = next(r for r in results if r.reason.related is not None)
    assert related.obj_ref == ref("parent")
    assert related.reason == ReconcileReason.related_object_updated(ref("child"))


async def test_a_controller_that_never_runs_never_holds_up_a_shared_watch() -> None:
    api = FakeApi(ConfigMap)
    api.pages.append(Page([cm("a", "1"), cm("b", "1")], resource_version="1"))
    api.watches.append([event("MODIFIED", cm("a", "2"))])
    with anyio.fail_after(5):
        async with shared_reflector(api.as_api()) as shared:
            # the smallest queue, never read: subscribed, it would stall the
            # writer on the second listed object
            Controller.for_shared(ConfigMap, shared, buffer=BoundedBuffer(size=1))
            Controller(ConfigMap, FakeApi(ConfigMap).as_api()).owns_shared(
                shared, buffer=BoundedBuffer(size=1)
            )
            while (a := shared.store.get_named("ns", "a")) is None or (
                a.metadata.resource_version != "2"
            ):
                await anyio.sleep(0.001)


async def test_adapt_wraps_a_shared_subscription_the_controller_closes() -> None:
    api = FakeApi(ConfigMap)
    api.pages.append(Page([cm("a"), cm("b")], resource_version="1"))
    subscriptions: list[AsyncIterable[ConfigMap]] = []

    def skip_b(stream: AsyncIterable[ConfigMap]) -> AsyncIterable[ConfigMap]:
        subscriptions.append(stream)
        # an async generator expression does not close the stream it reads
        return (obj async for obj in stream if obj.metadata.name != "b")

    with anyio.fail_after(5):
        async with shared_reflector(api.as_api()) as shared:
            controller = Controller.for_shared(ConfigMap, shared, adapt=skip_b)
            results = await collect_for(controller, Recorder(), 0.2)
            # the controller closed it when it stopped: iterating ends at once
            assert [obj async for obj in subscriptions[0]] == []
    assert [r.obj_ref for r in results] == [ref("a")]


async def test_warns_when_its_stores_stay_unready(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr("kubex_runtime.controller._applier._READY_WARNING_AFTER", 0.05)
    api = FakeApi(ConfigMap)
    api.pages.append(Page([cm("a")], resource_version="1"))
    late: Store[ConfigMap]
    late_writer: Writer[ConfigMap]
    late, late_writer = store()
    controller = Controller(ConfigMap, api.as_api()).waits_for(late)

    def warnings() -> list[logging.LogRecord]:
        return [r for r in caplog.records if "not ready" in r.getMessage()]

    with caplog.at_level(logging.WARNING, logger="kubex_runtime.controller"):
        with anyio.fail_after(5):
            async with controller.running(Recorder(), wait_for_change, None) as results:
                while not warnings():
                    await anyio.sleep(0.01)
                await late_writer.apply_watcher_event(Init())
                await late_writer.apply_watcher_event(InitDone())
                result = await results.receive()
    [record] = warnings()
    assert record.levelno == logging.WARNING
    assert record.name == "kubex_runtime.controller"
    assert record.getMessage().startswith("ConfigMap controller: 1 of 2 stores")
    assert result.obj_ref == ref("a")


async def test_watches_maps_related_objects_and_skips_a_failing_mapper(
    caplog: pytest.LogCaptureFixture,
) -> None:
    parents = FakeApi(ConfigMap)
    parents.pages.append(Page([cm("p")], resource_version="1"))
    others = FakeApi(ConfigMap)
    others.list_delay = 0.05
    others.pages.append(Page([cm("x"), cm("boom")], resource_version="1"))

    def mapper(obj: ConfigMap) -> list[ObjectRef]:
        if obj.metadata.name == "boom":
            raise ValueError("cannot map")
        return [ref("p")]

    controller = Controller(ConfigMap, parents.as_api()).watches(
        ConfigMap, others.as_api(), mapper
    )
    with caplog.at_level(logging.ERROR, logger="kubex_runtime.controller"):
        results = await collect_for(controller, Recorder(), 0.3)
    related = [r for r in results if r.reason.related is not None]
    assert [(r.obj_ref, r.reason.related) for r in related] == [(ref("p"), ref("x"))]
    failed = [
        r for r in caplog.records if "mapper failed for ns/boom" in r.getMessage()
    ]
    assert {r.name for r in failed} == {"kubex_runtime.controller"}


async def test_reconcile_on_and_reconcile_all_on() -> None:
    api = FakeApi(ConfigMap)
    api.pages.append(Page([cm("a"), cm("b")], resource_version="1"))
    controller = (
        Controller(ConfigMap, api.as_api())
        .reconcile_on(later([ref("a")], delay=0.05))
        .reconcile_all_on(later([None], delay=0.1))
    )
    results = await collect_for(controller, Recorder(), 0.3)
    reasons = [(r.obj_ref.name, r.reason) for r in results]
    assert ("a", UNKNOWN) in reasons
    assert ("a", BULK_RECONCILE) in reasons
    assert ("b", BULK_RECONCILE) in reasons


async def test_requeue_after_reconciles_again() -> None:
    api = FakeApi(ConfigMap)
    api.pages.append(Page([cm("a")], resource_version="1"))
    actions = [Action.requeue(0.01), Action.await_change()]

    async def reconcile(obj: ConfigMap, ctx: None) -> Action:
        return actions.pop(0)

    results = await collect(
        Controller(ConfigMap, api.as_api()), reconcile, lambda rs: len(rs) >= 2
    )
    assert (results[0].reason, results[0].action) == (
        OBJECT_UPDATED,
        Action.requeue(0.01),
    )
    assert results[1].reason == RECONCILER_REQUESTED_RETRY


async def test_an_error_goes_to_the_error_policy() -> None:
    api = FakeApi(ConfigMap)
    api.pages.append(Page([cm("a")], resource_version="1"))
    errors = [ValueError("first")]
    seen: list[tuple[str | None, Exception]] = []

    async def reconcile(obj: ConfigMap, ctx: None) -> Action:
        if errors:
            raise errors.pop()
        return Action.await_change()

    def policy(obj: ConfigMap, error: Exception, ctx: None) -> Action:
        seen.append((obj.metadata.name, error))
        return Action.requeue(0.01)

    results = await collect(
        Controller(ConfigMap, api.as_api()), reconcile, lambda rs: len(rs) >= 2, policy
    )
    assert isinstance(results[0].error, ValueError)
    assert results[0].action == Action.requeue(0.01)
    assert seen == [("a", results[0].error)]
    assert results[1].reason == ERROR_POLICY_REQUESTED_RETRY
    assert results[1].error is None


async def test_an_error_policy_that_raises_gives_no_action(
    caplog: pytest.LogCaptureFixture,
) -> None:
    api = FakeApi(ConfigMap)
    api.pages.append(Page([cm("a")], resource_version="1"))

    async def reconcile(obj: ConfigMap, ctx: None) -> Action:
        raise ValueError("reconcile")

    def policy(obj: ConfigMap, error: Exception, ctx: None) -> Action:
        raise RuntimeError("policy")

    with caplog.at_level(logging.ERROR, logger="kubex_runtime.controller"):
        results = await collect_for(
            Controller(ConfigMap, api.as_api()), reconcile, 0.15, policy
        )
    [result] = results
    assert isinstance(result.error, ValueError)
    assert result.action is None
    assert any("error policy failed" in r.getMessage() for r in caplog.records)


async def test_an_object_is_never_reconciled_twice_at_once() -> None:
    api = FakeApi(ConfigMap)
    api.pages.append(Page([cm("a")], resource_version="1"))
    triggers, receiver = anyio.create_memory_object_stream[ObjectRef](10)
    started = anyio.Event()
    release = anyio.Event()
    active = 0
    max_active = 0
    calls = 0

    async def reconcile(obj: ConfigMap, ctx: None) -> Action:
        nonlocal active, max_active, calls
        calls += 1
        active += 1
        max_active = max(max_active, active)
        try:
            if calls == 1:
                started.set()
                await release.wait()
        finally:
            active -= 1
        return Action.await_change()

    controller = Controller(ConfigMap, api.as_api()).reconcile_on(receiver)
    results: list[ReconcileResult] = []
    with anyio.fail_after(5):
        async with controller.running(reconcile, wait_for_change, None) as stream:
            await started.wait()
            await triggers.send(ref("a"))
            await triggers.send(ref("a"))
            await anyio.sleep(0.05)
            assert calls == 1
            release.set()
            async for result in stream:
                results.append(result)
                if len(results) == 2:
                    break
            await anyio.sleep(0.05)
            # the triggers that came meanwhile ran once, right after
            assert calls == 2
    assert max_active == 1
    assert [r.reason for r in results] == [OBJECT_UPDATED, UNKNOWN]


@pytest.mark.parametrize(("concurrency", "expected"), [(2, 2), (0, 5)])
async def test_concurrency_caps_the_reconciles_running_at_once(
    concurrency: int, expected: int
) -> None:
    api = FakeApi(ConfigMap)
    api.pages.append(Page([cm(name) for name in "abcde"], resource_version="1"))
    active = 0
    max_active = 0

    async def reconcile(obj: ConfigMap, ctx: None) -> Action:
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await anyio.sleep(0.02)
        active -= 1
        return Action.await_change()

    controller = Controller(ConfigMap, api.as_api()).with_config(
        ControllerConfig(concurrency=concurrency)
    )
    results = await collect(controller, reconcile, lambda rs: len(rs) >= 5)
    assert {r.obj_ref.name for r in results} == set("abcde")
    assert max_active == expected


async def test_debounce_merges_a_burst_of_triggers() -> None:
    api = FakeApi(ConfigMap)
    api.pages.append(Page([cm("a")], resource_version="1"))
    triggers, receiver = anyio.create_memory_object_stream[ObjectRef](10)
    controller = (
        Controller(ConfigMap, api.as_api())
        .reconcile_on(receiver)
        .with_config(ControllerConfig(debounce=0.05))
    )
    rest: list[ReconcileResult] = []
    with anyio.fail_after(5):
        async with controller.running(Recorder(), wait_for_change, None) as stream:
            first = await stream.receive()
            for _ in range(5):
                await triggers.send(ref("a"))
                await anyio.sleep(0.01)
            with anyio.move_on_after(0.3):
                async for result in stream:
                    rest.append(result)
    assert first.reason == OBJECT_UPDATED
    assert [r.reason for r in rest] == [UNKNOWN]


async def test_a_trigger_for_an_object_not_in_the_store_is_dropped() -> None:
    api = FakeApi(ConfigMap)
    api.pages.append(Page([cm("a")], resource_version="1"))
    reconcile = Recorder()
    controller = Controller(ConfigMap, api.as_api()).reconcile_on(
        later([ref("ghost"), ref("a", namespace="other")], delay=0.02)
    )
    await collect_for(controller, reconcile, 0.15)
    assert reconcile.calls == [("a", "1")]


@pytest.mark.parametrize(
    "buffer",
    [
        pytest.param(BoundedBuffer(size=1), id="bounded-1"),
        pytest.param(MergedBuffer(), id="merged"),
    ],
)
async def test_a_shared_stream_controller_closes_its_subscription(
    buffer: SubscriberBuffer,
) -> None:
    reader: Store[ConfigMap]
    writer: Writer[ConfigMap]
    reader, writer = store()
    subscription = writer.subscribe(buffer)
    controller = Controller.for_shared_stream(ConfigMap, subscription, reader)
    reconcile = Recorder()
    with anyio.fail_after(5):
        async with controller.running(reconcile, wait_for_change, None) as results:
            await writer.apply_watcher_event(Init())
            await writer.apply_watcher_event(InitApply(cm("a", "1")))
            await writer.apply_watcher_event(InitDone())
            await results.receive()
            await writer.apply_watcher_event(Apply(cm("a", "2")))
            await results.receive()
        # nothing reads the subscription any more: a bounded one, still open,
        # would make the writer wait once full
        for version in range(10, 20):
            await writer.apply_watcher_event(Apply(cm("a", str(version))))
    assert reconcile.calls == [("a", "1"), ("a", "2")]
    assert [obj async for obj in subscription] == []


async def test_a_watch_that_gives_up_ends_running_with_its_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        WATCHER_MODULE,
        "default_backoff",
        lambda: ExponentialBackoff(initial=0, jitter=False, max_retries=0),
    )
    api = FakeApi(ConfigMap)
    api.pages.append(build_exception(500, "boom"))
    controller = Controller(ConfigMap, api.as_api())
    with anyio.fail_after(5), pytest.raises(KubernetesError):
        async with controller.running(Recorder(), wait_for_change, None) as results:
            async for _ in results:
                pass


async def test_an_owned_watch_that_gives_up_ends_run_with_its_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        WATCHER_MODULE,
        "default_backoff",
        lambda: ExponentialBackoff(initial=0, jitter=False, max_retries=0),
    )
    api = FakeApi(ConfigMap)
    api.pages.append(Page([cm("a")], resource_version="1"))
    owned = FakeApi(ConfigMap)
    owned.pages.append(build_exception(500, "boom"))
    controller = Controller(ConfigMap, api.as_api()).owns(ConfigMap, owned.as_api())
    with anyio.fail_after(5), pytest.raises(KubernetesError):
        await controller.run(Recorder(), wait_for_change, None)
    assert api.open_watches == 0


async def test_a_failing_trigger_stream_ends_running_with_its_error() -> None:
    api = FakeApi(ConfigMap)
    api.pages.append(Page([cm("a")], resource_version="1"))

    async def broken() -> AsyncIterator[ObjectRef]:
        await anyio.sleep(0.01)
        raise LookupError("trigger source broke")
        yield ref("a")  # pragma: no cover

    controller = Controller(ConfigMap, api.as_api()).reconcile_on(broken())
    with anyio.fail_after(5), pytest.raises(LookupError, match="trigger source broke"):
        async with controller.running(Recorder(), wait_for_change, None) as results:
            async for _ in results:
                pass


async def test_an_error_ending_running_keeps_its_cause(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        WATCHER_MODULE,
        "default_backoff",
        lambda: ExponentialBackoff(initial=0, jitter=False, max_retries=0),
    )
    cause = OSError("connection reset")
    error = KubexConnectionError("connecting failed")
    error.__cause__ = cause
    api = FakeApi(ConfigMap)
    api.pages.append(error)
    controller = Controller(ConfigMap, api.as_api())
    with anyio.fail_after(5), pytest.raises(KubexConnectionError) as raised:
        async with controller.running(Recorder(), wait_for_change, None) as results:
            async for _ in results:
                pass
    assert raised.value is error
    assert raised.value.__cause__ is cause


async def test_an_error_of_the_running_block_keeps_its_context() -> None:
    api = FakeApi(ConfigMap)
    api.pages.append(Page([cm("a")], resource_version="1"))
    controller = Controller(ConfigMap, api.as_api())
    with anyio.fail_after(5), pytest.raises(LookupError) as raised:
        async with controller.running(Recorder(), wait_for_change, None):
            try:
                raise KeyError("first")
            except KeyError:
                raise LookupError("second")
    assert isinstance(raised.value.__context__, KeyError)
    assert raised.value.__cause__ is None


def test_a_controller_needs_an_api() -> None:
    # without a watch of its own nothing would fill its store
    with pytest.raises(TypeError):
        Controller(ConfigMap)  # type: ignore[call-arg]


async def test_leaving_running_cancels_reconciles_and_closes_watches() -> None:
    api = FakeApi(ConfigMap)
    api.pages.append(Page([cm("a")], resource_version="1"))
    owned = FakeApi(ConfigMap)
    owned.pages.append(Page([], resource_version="1"))
    started = anyio.Event()
    cancelled: list[str | None] = []

    async def reconcile(obj: ConfigMap, ctx: None) -> Action:
        started.set()
        try:
            await anyio.sleep_forever()
        except anyio.get_cancelled_exc_class():
            cancelled.append(obj.metadata.name)
            raise
        return Action.await_change()

    controller = Controller(ConfigMap, api.as_api()).owns(ConfigMap, owned.as_api())
    with anyio.fail_after(5):
        async with controller.running(reconcile, wait_for_change, None):
            await started.wait()
            while api.open_watches != 1 or owned.open_watches != 1:
                await anyio.sleep(0.001)
    assert cancelled == ["a"]
    assert api.open_watches == 0
    assert owned.open_watches == 0


async def test_run_logs_failed_reconciles(caplog: pytest.LogCaptureFixture) -> None:
    api = FakeApi(ConfigMap)
    api.pages.append(Page([cm("a")], resource_version="1"))

    async def reconcile(obj: ConfigMap, ctx: None) -> Action:
        raise ValueError("nope")

    with caplog.at_level(logging.ERROR, logger="kubex_runtime.controller"):
        with anyio.move_on_after(0.2):
            await Controller(ConfigMap, api.as_api()).run(
                reconcile, wait_for_change, None
            )
    [record] = [r for r in caplog.records if "failed" in r.getMessage()]
    assert record.levelno == logging.ERROR
    assert record.name == "kubex_runtime.controller"
    assert "ns/a" in record.getMessage()
    assert record.exc_info
    assert isinstance(record.exc_info[1], ValueError)


# -- writes recorded for an object -------------------------------------------------

PARENT = cm("parent", uid="uid-parent")


async def listed(*objects: ConfigMap) -> tuple[Store[ConfigMap], Writer[ConfigMap]]:
    """A store that has listed `objects` at version 5."""
    reader: Store[ConfigMap]
    writer: Writer[ConfigMap]
    reader, writer = store()
    await writer.apply_watcher_event(Init())
    for obj in objects:
        await writer.apply_watcher_event(InitApply(obj))
    await writer.apply_watcher_event(InitDone("5"))
    return reader, writer


async def nothing_within(results: AsyncIterator[ReconcileResult]) -> bool:
    """Whether no result comes for a while."""
    with anyio.move_on_after(0.05) as scope:
        await anext(results)
    return scope.cancelled_caught


def on_parents(
    parents: Store[ConfigMap], parent_writer: Writer[ConfigMap]
) -> Controller[ConfigMap]:
    return Controller.for_shared_stream(
        ConfigMap, parent_writer.subscribe(MergedBuffer()), parents
    )


async def test_an_owner_is_held_until_its_stores_have_seen_its_writes() -> None:
    parents, parent_writer = await listed(PARENT)
    children, child_writer = await listed()
    seen: list[list[str | None]] = []

    async def reconcile(obj: ConfigMap, ctx: None) -> Action:
        seen.append([child.metadata.name for child in children.state()])
        if not children.state():
            children.wrote(cm("child", "10"), owner=obj)
            return Action.requeue(0)
        return Action.await_change()

    controller = on_parents(parents, parent_writer).waits_for(children)
    with anyio.fail_after(5):
        async with controller.running(reconcile, wait_for_change, None) as results:
            await results.receive()
            # requeued at once, and held: the child store has not seen the child
            assert await nothing_within(results)
            await child_writer.apply_watcher_event(Apply(cm("child", "10")))
            second = await results.receive()
    assert seen == [[], ["child"]]
    assert second.reason == RECONCILER_REQUESTED_RETRY


async def test_a_reconcile_that_fails_after_writing_is_retried_once_seen() -> None:
    parents, parent_writer = await listed(PARENT)
    children, child_writer = await listed()
    seen: list[int] = []

    async def reconcile(obj: ConfigMap, ctx: None) -> Action:
        seen.append(len(children.state()))
        if len(seen) == 1:
            children.wrote(cm("child", "10"), owner=obj)
            raise ValueError("the status update failed")
        return Action.await_change()

    def retry(obj: ConfigMap, error: Exception, ctx: None) -> Action:
        return Action.requeue(0)

    controller = on_parents(parents, parent_writer).waits_for(children)
    with anyio.fail_after(5):
        async with controller.running(reconcile, retry, None) as results:
            first = await results.receive()
            assert await nothing_within(results)
            await child_writer.apply_watcher_event(Apply(cm("child", "10")))
            second = await results.receive()
    assert isinstance(first.error, ValueError)
    assert second.reason == ERROR_POLICY_REQUESTED_RETRY
    assert seen == [0, 1]


async def test_a_held_owner_takes_no_place_under_the_concurrency_cap() -> None:
    other = cm("other", uid="uid-other")
    parents, parent_writer = await listed(PARENT, other)
    children, child_writer = await listed()
    children.wrote(cm("child", "10"), owner=PARENT)
    controller = (
        on_parents(parents, parent_writer)
        .waits_for(children)
        .with_config(ControllerConfig(concurrency=1))
    )
    with anyio.fail_after(5):
        async with controller.running(Recorder(), wait_for_change, None) as results:
            first = await results.receive()
            assert await nothing_within(results)
            await child_writer.apply_watcher_event(Apply(cm("child", "10")))
            second = await results.receive()
    assert [first.obj_ref, second.obj_ref] == [ref("other"), ref("parent")]


async def test_triggers_for_a_held_owner_make_one_reconcile() -> None:
    parents, parent_writer = await listed(PARENT)
    children, child_writer = await listed()
    children.wrote(cm("child", "10"), owner=PARENT)
    send, receive = anyio.create_memory_object_stream[ObjectRef](10)
    controller = (
        on_parents(parents, parent_writer).waits_for(children).reconcile_on(receive)
    )
    with anyio.fail_after(5):
        async with controller.running(Recorder(), wait_for_change, None) as results:
            for _ in range(3):
                await send.send(ref("parent"))
            assert await nothing_within(results)
            await child_writer.apply_watcher_event(Apply(cm("child", "10")))
            result = await results.receive()
            assert await nothing_within(results)
    # the first trigger: the subscription's
    assert result.reason == OBJECT_UPDATED


async def test_a_write_to_the_object_itself_holds_it() -> None:
    parents, parent_writer = await listed(PARENT)
    parents.wrote(cm("parent", "10", uid="uid-parent"), owner=PARENT)
    reconcile = Recorder()
    controller = on_parents(parents, parent_writer)
    with anyio.fail_after(5):
        async with controller.running(reconcile, wait_for_change, None) as results:
            assert await nothing_within(results)
            await parent_writer.apply_watcher_event(
                Apply(cm("parent", "10", uid="uid-parent"))
            )
            await results.receive()
            assert await nothing_within(results)
    # never reconciled against the state from before its own write
    assert reconcile.calls == [("parent", "10")]


async def test_warns_when_an_owner_stays_held_for_its_writes(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(
        "kubex_runtime.controller._applier._UNSEEN_WRITES_WARNING_AFTER", 0.05
    )
    parents, parent_writer = await listed(PARENT)
    children, child_writer = await listed()
    children.wrote(cm("child", "10"), owner=PARENT)
    controller = on_parents(parents, parent_writer).waits_for(children)

    def warnings() -> list[logging.LogRecord]:
        return [r for r in caplog.records if "own writes" in r.getMessage()]

    with caplog.at_level(logging.WARNING, logger="kubex_runtime.controller"):
        with anyio.fail_after(5):
            async with controller.running(Recorder(), wait_for_change, None) as results:
                while not warnings():
                    await anyio.sleep(0.01)
                assert await nothing_within(results)
                await child_writer.apply_watcher_event(Apply(cm("child", "10")))
                result = await results.receive()
    [record] = warnings()
    assert record.levelno == logging.WARNING
    assert record.getMessage().startswith(
        "ConfigMap controller: ConfigMap.core ns/parent held 0s for its own writes, "
        "1 of 1 stores"
    )
    assert result.obj_ref == ref("parent")


async def test_an_owner_deleted_while_held_is_dropped() -> None:
    parents, parent_writer = await listed(PARENT)
    children, child_writer = await listed()
    children.wrote(cm("child", "10"), owner=PARENT)
    controller = on_parents(parents, parent_writer).waits_for(children)
    with anyio.fail_after(5):
        async with controller.running(Recorder(), wait_for_change, None) as results:
            assert await nothing_within(results)
            await parent_writer.apply_watcher_event(Delete(PARENT))
            await child_writer.apply_watcher_event(Apply(cm("child", "10")))
            assert await nothing_within(results)


async def test_leaving_running_with_an_owner_held_ends_cleanly() -> None:
    parents, parent_writer = await listed(PARENT)
    children, _ = await listed()
    children.wrote(cm("child", "10"), owner=PARENT)
    controller = on_parents(parents, parent_writer).waits_for(children)
    with anyio.fail_after(5):
        async with controller.running(Recorder(), wait_for_change, None) as results:
            assert await nothing_within(results)
    assert children._pending("uid-parent")


async def test_an_owner_re_created_under_its_name_is_not_held_by_the_old_writes() -> (
    None
):
    parents, parent_writer = await listed(PARENT)
    children, child_writer = await listed()
    children.wrote(cm("child", "10"), owner=PARENT)
    reconcile = Recorder()
    controller = on_parents(parents, parent_writer).waits_for(children)
    with anyio.fail_after(5):
        async with controller.running(reconcile, wait_for_change, None) as results:
            assert await nothing_within(results)
            # re-created under its name, the deletion missed (as by a re-list)
            await parent_writer.apply_watcher_event(
                Apply(cm("parent", "7", uid="uid-new"))
            )
            await results.receive()
            # the old owner's write, seen at last, schedules nothing more
            await child_writer.apply_watcher_event(Apply(cm("child", "10")))
            assert await nothing_within(results)
    assert reconcile.calls == [("parent", "7")]


async def test_an_owner_re_created_under_its_name_is_held_by_its_own_writes() -> None:
    parents, parent_writer = await listed(PARENT)
    children, child_writer = await listed()
    children.wrote(cm("child", "10"), owner=PARENT)
    new = cm("parent", "7", uid="uid-new")
    reconcile = Recorder()
    controller = on_parents(parents, parent_writer).waits_for(children)
    with anyio.fail_after(5):
        async with controller.running(reconcile, wait_for_change, None) as results:
            assert await nothing_within(results)
            children.wrote(cm("child-2", "20"), owner=new)
            await parent_writer.apply_watcher_event(Apply(new))
            assert await nothing_within(results)
            # the old owner's write releases nothing: the new one waits for its own
            await child_writer.apply_watcher_event(Apply(cm("child", "10")))
            assert await nothing_within(results)
            await child_writer.apply_watcher_event(Apply(cm("child-2", "20")))
            await results.receive()
    assert reconcile.calls == [("parent", "7")]


async def test_no_warning_for_the_writes_of_an_owner_re_created_since(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    # past the 0.05 s the test waits while the old owner is held
    monkeypatch.setattr(
        "kubex_runtime.controller._applier._UNSEEN_WRITES_WARNING_AFTER", 0.1
    )
    parents, parent_writer = await listed(PARENT)
    children, _ = await listed()
    children.wrote(cm("child", "10"), owner=PARENT)
    controller = on_parents(parents, parent_writer).waits_for(children)
    with caplog.at_level(logging.WARNING, logger="kubex_runtime.controller"):
        with anyio.fail_after(5):
            async with controller.running(Recorder(), wait_for_change, None) as results:
                assert await nothing_within(results)
                await parent_writer.apply_watcher_event(
                    Apply(cm("parent", "7", uid="uid-new"))
                )
                await results.receive()
                # the old owner's wait ended with its hold, before the mark
                await anyio.wait_all_tasks_blocked()
                assert len(children._version_waiters) == 0
                await anyio.sleep(0.15)
    assert not [r for r in caplog.records if "own writes" in r.getMessage()]


@pytest.mark.parametrize(
    "replacement",
    [None, cm("parent", "7", uid="uid-new")],
    ids=["deleted", "re-created"],
)
async def test_a_dropped_hold_stops_waiting_past_the_warning(
    replacement: ConfigMap | None,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(
        "kubex_runtime.controller._applier._UNSEEN_WRITES_WARNING_AFTER", 0.05
    )
    parents, parent_writer = await listed(PARENT)
    children, _ = await listed()
    children.wrote(cm("child", "10"), owner=PARENT)
    controller = on_parents(parents, parent_writer).waits_for(children)
    gone: Event[ConfigMap] = (
        Delete(PARENT) if replacement is None else Apply(replacement)
    )
    with caplog.at_level(logging.WARNING, logger="kubex_runtime.controller"):
        with anyio.fail_after(5):
            async with controller.running(Recorder(), wait_for_change, None):
                # warned: the hold now waits with no deadline
                while not [r for r in caplog.records if "own writes" in r.getMessage()]:
                    await anyio.sleep(0.01)
                assert len(children._version_waiters) == 1
                await parent_writer.apply_watcher_event(gone)
                while len(children._version_waiters):
                    await anyio.sleep(0.01)


async def test_forget_writes_releases_an_owner_held_for_them() -> None:
    parents, parent_writer = await listed(PARENT)
    children, _ = await listed()
    children.wrote(cm("child", "10"), owner=PARENT)
    controller = on_parents(parents, parent_writer).waits_for(children)
    with anyio.fail_after(5):
        async with controller.running(Recorder(), wait_for_change, None) as results:
            assert await nothing_within(results)
            # the child's cluster is gone for good: its store will never see it
            children.forget_writes()
            result = await results.receive()
    assert result.obj_ref == ref("parent")
