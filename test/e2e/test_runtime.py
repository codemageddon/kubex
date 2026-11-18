"""E2E: kubex_runtime controllers against K3S.

A ConfigMap controller with a finalizer that creates an owned child, a
Namespace controller triggered by a ConfigMap the namespace owns (a namespaced
dependent of a cluster-scoped owner), two controllers over a chain of owners
sharing one reflector per level, a parent that requeues itself right after
creating a child with a generated name (the controllers use the default
strategy, a streaming list with a fallback), and a watcher started with each
initial list strategy.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import aclosing
from typing import cast

import anyio
import pytest
from anyio.streams.memory import MemoryObjectReceiveStream

from kubex.api import Api
from kubex.client import BaseClient
from kubex.core.exceptions import Conflict, NotFound
from kubex.core.patch import MergePatch
from kubex.k8s.v1_35.core.v1.config_map import ConfigMap
from kubex.k8s.v1_35.core.v1.namespace import Namespace
from kubex_core.models.metadata import ObjectMetadata, OwnerReference
from kubex_runtime import (
    Action,
    Apply,
    Controller,
    Event,
    FinalizerApply,
    FinalizerCleanup,
    FinalizerEvent,
    Init,
    InitApply,
    InitDone,
    InitialListStrategy,
    ObjectRef,
    ReconcileResult,
    Store,
    WatcherConfig,
    finalizer,
    shared_reflector,
    watcher,
)

pytestmark = pytest.mark.anyio

_TIMEOUT = 60
_ROLE = "runtime.kubex.test/role"
_FINALIZER = "runtime.kubex.test/cleanup"


@pytest.fixture(params=["asyncio", "trio"])
def anyio_backend(request: pytest.FixtureRequest) -> str:
    return str(request.param)


async def _eventually(check: Callable[[], Awaitable[bool]]) -> None:
    with anyio.fail_after(_TIMEOUT):
        while not await check():
            await anyio.sleep(0.2)


async def _collect(
    results: MemoryObjectReceiveStream[ReconcileResult], into: list[ReconcileResult]
) -> None:
    async for result in results:
        into.append(result)


def _controller_of(obj: ConfigMap | Namespace, kind: str) -> OwnerReference:
    assert obj.metadata.name is not None and obj.metadata.uid is not None
    return OwnerReference(
        api_version="v1",
        kind=kind,
        name=obj.metadata.name,
        uid=obj.metadata.uid,
        controller=True,
    )


async def _exists(api: Api[ConfigMap], name: str) -> bool:
    try:
        await api.get(name)
    except NotFound:
        return False
    return True


def _retry(_: object, __: Exception, ___: None) -> Action:
    return Action.requeue(0.5)


async def test_controller_with_finalizer_and_owned_child(
    client: BaseClient, tmp_namespace_name: str
) -> None:
    api: Api[ConfigMap] = Api(ConfigMap, client=client, namespace=tmp_namespace_name)
    cleaned: list[str] = []

    async def ensure_child(parent: ConfigMap) -> None:
        name = f"{parent.metadata.name}-child"
        if await _exists(api, name):
            return
        child = ConfigMap(
            metadata=ObjectMetadata(
                name=name,
                labels={_ROLE: "child"},
                owner_references=[_controller_of(parent, "ConfigMap")],
            )
        )
        try:
            await api.create(child)
        except Conflict:
            pass  # created by an earlier reconcile

    async def handle(event: FinalizerEvent[ConfigMap]) -> Action:
        match event:
            case FinalizerApply(obj):
                await ensure_child(obj)
            case FinalizerCleanup(obj):
                assert obj.metadata.name is not None
                cleaned.append(obj.metadata.name)
        return Action.await_change()

    async def reconcile(obj: ConfigMap, _: None) -> Action:
        return await finalizer(api, _FINALIZER, obj, handle)

    controller = Controller(
        ConfigMap, api, WatcherConfig(label_selector=f"{_ROLE}=parent")
    ).owns(ConfigMap, api, WatcherConfig(label_selector=f"{_ROLE}=child"))
    seen: list[ReconcileResult] = []
    async with controller.running(reconcile, _retry, None) as results:
        async with anyio.create_task_group() as group:
            group.start_soon(_collect, results, seen)
            await api.create(
                ConfigMap(
                    metadata=ObjectMetadata(name="parent", labels={_ROLE: "parent"})
                )
            )

            async def finalized_with_child() -> bool:
                parent = await api.get("parent")
                return _FINALIZER in (
                    parent.metadata.finalizers or []
                ) and await _exists(api, "parent-child")

            await _eventually(finalized_with_child)

            # a change of the child reconciles its owner
            await api.patch(
                "parent-child",
                MergePatch(
                    ConfigMap.model_validate({"metadata": {}, "data": {"k": "v"}})
                ),
            )
            child_ref = ObjectRef.of(ConfigMap, "parent-child", tmp_namespace_name)

            async def owner_reconciled() -> bool:
                return any(r.reason.related == child_ref for r in seen)

            await _eventually(owner_reconciled)

            # deleting runs the cleanup, then the finalizer lets the object go
            await api.delete("parent")

            async def parent_gone() -> bool:
                return not await _exists(api, "parent")

            await _eventually(parent_gone)
            assert cleaned == ["parent"]
            assert all(r.error is None for r in seen), [r.error for r in seen]
            group.cancel_scope.cancel()


async def test_cluster_scoped_owner_is_reconciled(
    client: BaseClient, tmp_namespace_name: str
) -> None:
    namespaces: Api[Namespace] = Api(Namespace, client=client)
    config_maps: Api[ConfigMap] = Api(
        ConfigMap, client=client, namespace=tmp_namespace_name
    )
    # watch only this test's namespace
    namespace = await namespaces.patch(
        tmp_namespace_name,
        MergePatch(Namespace(metadata=ObjectMetadata(labels={_ROLE: "owner"}))),
    )
    reconciled: list[str] = []

    async def reconcile(obj: Namespace, _: None) -> Action:
        assert obj.metadata.name is not None
        reconciled.append(obj.metadata.name)
        return Action.await_change()

    controller = Controller(
        Namespace,
        namespaces,
        WatcherConfig(label_selector=f"{_ROLE}=owner"),
    ).owns(ConfigMap, config_maps, WatcherConfig(label_selector=f"{_ROLE}=owned"))
    seen: list[ReconcileResult] = []
    async with controller.running(reconcile, _retry, None) as results:
        async with anyio.create_task_group() as group:
            group.start_soon(_collect, results, seen)

            async def namespace_reconciled() -> bool:
                return tmp_namespace_name in reconciled

            await _eventually(namespace_reconciled)

            await config_maps.create(
                ConfigMap(
                    metadata=ObjectMetadata(
                        name="owned",
                        labels={_ROLE: "owned"},
                        owner_references=[_controller_of(namespace, "Namespace")],
                    )
                )
            )
            owned_ref = ObjectRef.of(ConfigMap, "owned", tmp_namespace_name)
            owner_ref = ObjectRef.of(Namespace, tmp_namespace_name)

            async def owner_reconciled() -> bool:
                return any(
                    r.reason.related == owned_ref and r.obj_ref == owner_ref
                    for r in seen
                )

            await _eventually(owner_reconciled)
            group.cancel_scope.cancel()


async def test_controllers_sharing_reflectors_over_a_chain_of_owners(
    client: BaseClient, tmp_namespace_name: str
) -> None:
    """parent -> child -> grandchild, a controller per owner level, each owner
    reading its children from the shared store it is triggered from."""
    api: Api[ConfigMap] = Api(ConfigMap, client=client, namespace=tmp_namespace_name)

    def role(name: str) -> WatcherConfig:
        return WatcherConfig(label_selector=f"{_ROLE}={name}")

    async def ensure_child(
        owner: ConfigMap, owned: Store[ConfigMap], kind: str
    ) -> None:
        name = f"{owner.metadata.name}-{kind}"
        if owned.get_named(tmp_namespace_name, name) is not None:
            return
        child = ConfigMap(
            metadata=ObjectMetadata(
                name=name,
                labels={_ROLE: kind},
                owner_references=[_controller_of(owner, "ConfigMap")],
            )
        )
        try:
            await api.create(child)
        except Conflict:
            pass  # the store had not seen an earlier create yet

    gc_name = "p-child-grandchild"
    seen: list[ReconcileResult] = []
    async with (
        shared_reflector(api, role("parent")) as parents,
        shared_reflector(api, role("child")) as children,
        shared_reflector(api, role("grandchild")) as grandchildren,
    ):

        async def reconcile_parent(obj: ConfigMap, _: None) -> Action:
            await ensure_child(obj, children.store, "child")
            return Action.await_change()

        async def reconcile_child(obj: ConfigMap, _: None) -> Action:
            await ensure_child(obj, grandchildren.store, "grandchild")
            return Action.await_change()

        parent_controller = Controller.for_shared(ConfigMap, parents).owns_shared(
            children
        )
        child_controller = Controller.for_shared(ConfigMap, children).owns_shared(
            grandchildren
        )
        async with (
            parent_controller.running(reconcile_parent, _retry, None) as parent_results,
            child_controller.running(reconcile_child, _retry, None) as child_results,
            anyio.create_task_group() as group,
        ):
            group.start_soon(_collect, parent_results, seen)
            group.start_soon(_collect, child_results, seen)
            await api.create(
                ConfigMap(metadata=ObjectMetadata(name="p", labels={_ROLE: "parent"}))
            )
            await _eventually(lambda: _exists(api, gc_name))

            # deleting the grandchild reconciles its owner, which recreates it
            old_uid = (await api.get(gc_name)).metadata.uid
            await api.delete(gc_name)

            async def recreated() -> bool:
                try:
                    obj = await api.get(gc_name)
                except NotFound:
                    return False
                return obj.metadata.uid != old_uid

            await _eventually(recreated)
            child_ref = ObjectRef.of(ConfigMap, "p-child", tmp_namespace_name)
            gc_ref = ObjectRef.of(ConfigMap, gc_name, tmp_namespace_name)
            assert any(
                r.obj_ref == child_ref and r.reason.related == gc_ref for r in seen
            )
            assert all(r.error is None for r in seen), [r.error for r in seen]
            group.cancel_scope.cancel()


async def test_children_with_generated_names_are_not_created_twice(
    client: BaseClient, tmp_namespace_name: str
) -> None:
    """Parents create their child with a generated name and requeue themselves
    at once, again and again: held until the child store has seen the child,
    none finds that store without it and creates a second one."""
    api: Api[ConfigMap] = Api(ConfigMap, client=client, namespace=tmp_namespace_name)
    parent_names = [f"p-{i}" for i in range(5)]
    rounds = 20
    reconciles: dict[str, int] = {}
    seen: list[ReconcileResult] = []
    async with (
        shared_reflector(
            api, WatcherConfig(label_selector=f"{_ROLE}=generating")
        ) as parents,
        shared_reflector(
            api, WatcherConfig(label_selector=f"{_ROLE}=generated")
        ) as children,
    ):

        async def reconcile(obj: ConfigMap, _: None) -> Action:
            name = obj.metadata.name or ""
            reconciles[name] = reconciles.get(name, 0) + 1
            uid = obj.metadata.uid
            mine = children.store.find(
                lambda child: any(
                    ref.uid == uid for ref in child.metadata.owner_references or ()
                )
            )
            if not mine:
                created = await api.create(
                    ConfigMap(
                        metadata=ObjectMetadata(
                            generate_name="generated-",
                            labels={_ROLE: "generated"},
                            owner_references=[_controller_of(obj, "ConfigMap")],
                        )
                    )
                )
                children.wrote(created, owner=obj)
            if reconciles[name] < rounds:
                return Action.requeue(0)
            return Action.await_change()

        async def done() -> bool:
            return all(reconciles.get(name, 0) >= rounds for name in parent_names)

        controller = Controller.for_shared(ConfigMap, parents).owns_shared(children)
        async with (
            controller.running(reconcile, _retry, None) as results,
            anyio.create_task_group() as group,
        ):
            group.start_soon(_collect, results, seen)
            for name in parent_names:
                await api.create(
                    ConfigMap(
                        metadata=ObjectMetadata(name=name, labels={_ROLE: "generating"})
                    )
                )
            await _eventually(done)
            group.cancel_scope.cancel()

    generated = await api.list(label_selector=f"{_ROLE}=generated")
    owners = [
        ref.name
        for child in generated.items
        for ref in child.metadata.owner_references or ()
    ]
    assert sorted(owners) == parent_names
    assert all(r.error is None for r in seen), [r.error for r in seen]


@pytest.mark.parametrize(
    "strategy", [InitialListStrategy.STREAMING_LIST, InitialListStrategy.LIST_WATCH]
)
async def test_watcher_initial_list_strategies(
    client: BaseClient, tmp_namespace_name: str, strategy: InitialListStrategy
) -> None:
    api: Api[ConfigMap] = Api(ConfigMap, client=client, namespace=tmp_namespace_name)
    labels = {_ROLE: "streamed"}
    for name in ("cm-1", "cm-2"):
        await api.create(ConfigMap(metadata=ObjectMetadata(name=name, labels=labels)))

    config = WatcherConfig(
        label_selector=f"{_ROLE}=streamed",
        page_size=1,  # two pages for LIST_WATCH; a streaming list ignores it
        initial_list_strategy=strategy,
    )
    stream = cast(AsyncGenerator[Event[ConfigMap], None], watcher(api, config))
    events: list[Event[ConfigMap]] = []
    with anyio.fail_after(_TIMEOUT):
        async with aclosing(stream):
            async for e in stream:
                events.append(e)
                if isinstance(e, InitDone):
                    await api.create(
                        ConfigMap(metadata=ObjectMetadata(name="cm-3", labels=labels))
                    )
                if isinstance(e, Apply) and e.obj.metadata.name == "cm-3":
                    break

    assert isinstance(events[0], Init)
    done = next(i for i, e in enumerate(events) if isinstance(e, InitDone))
    listed = {e.obj.metadata.name for e in events[:done] if isinstance(e, InitApply)}
    assert listed == {"cm-1", "cm-2"}
    assert not any(
        isinstance(e, (Init, InitApply, InitDone)) for e in events[done + 1 :]
    )
