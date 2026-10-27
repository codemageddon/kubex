"""E2E: objects that do not fit the model, and the end of a watch's initial events.

A custom resource whose CRD accepts any ``spec`` stands in for an object stored
before its CRD schema changed: ``LooseGadget`` writes a ``spec.replicas`` that
the stricter ``Gadget`` model rejects.
"""

from __future__ import annotations

from typing import Any, ClassVar, Literal

import anyio
import pytest
from pydantic import Field, ValidationError

from kubex.api import Api
from kubex.client import BaseClient
from kubex.core.exceptions import Conflict, NotFound, TooManyRequests
from kubex.core.params import InvalidObjects
from kubex.core.watch_event import EventType, InvalidWatchEvent, WatchEvent
from kubex.k8s.v1_35.apiextensions_k8s_io.v1.custom_resource_definition import (
    CustomResourceDefinition,
)
from kubex.k8s.v1_35.core.v1.config_map import ConfigMap
from kubex_core.models.base import BaseK8sModel
from kubex_core.models.interfaces import NamespaceScopedEntity
from kubex_core.models.metadata import ObjectMetadata
from kubex_core.models.resource_config import ResourceConfig, Scope

pytestmark = pytest.mark.anyio

_GROUP = "invalid-objects.kubex.test"
_CRD_NAME = f"gadgets.{_GROUP}"
_TIMEOUT = 60


class GadgetSpec(BaseK8sModel):
    replicas: int


class Gadget(NamespaceScopedEntity):
    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["Gadget"]] = ResourceConfig(
        version="v1",
        kind="Gadget",
        group=_GROUP,
        plural="gadgets",
        scope=Scope.NAMESPACE,
    )
    api_version: Literal["invalid-objects.kubex.test/v1"] = Field(
        default="invalid-objects.kubex.test/v1", alias="apiVersion"
    )
    kind: Literal["Gadget"] = Field(default="Gadget")
    spec: GadgetSpec | None = None


class LooseGadget(NamespaceScopedEntity):
    """The same resource with any ``spec``: writes objects ``Gadget`` rejects."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["LooseGadget"]] = ResourceConfig(
        version="v1",
        kind="Gadget",
        group=_GROUP,
        plural="gadgets",
        scope=Scope.NAMESPACE,
    )
    api_version: Literal["invalid-objects.kubex.test/v1"] = Field(
        default="invalid-objects.kubex.test/v1", alias="apiVersion"
    )
    kind: Literal["Gadget"] = Field(default="Gadget")
    spec: dict[str, Any] | None = None


_CRD = {
    "apiVersion": "apiextensions.k8s.io/v1",
    "kind": "CustomResourceDefinition",
    "metadata": {"name": _CRD_NAME},
    "spec": {
        "group": _GROUP,
        "scope": "Namespaced",
        "names": {"plural": "gadgets", "singular": "gadget", "kind": "Gadget"},
        "versions": [
            {
                "name": "v1",
                "served": True,
                "storage": True,
                "schema": {
                    "openAPIV3Schema": {
                        "type": "object",
                        "properties": {
                            "spec": {
                                "type": "object",
                                "x-kubernetes-preserve-unknown-fields": True,
                            }
                        },
                    }
                },
            }
        ],
    },
}


@pytest.fixture
async def gadgets(
    client: BaseClient, tmp_namespace_name: str
) -> tuple[Api[Gadget], Api[LooseGadget]]:
    """Install the CRD (once per cluster) and create a valid and an invalid gadget."""
    crd_api: Api[CustomResourceDefinition] = Api(
        CustomResourceDefinition, client=client
    )
    try:
        await crd_api.create(CustomResourceDefinition.model_validate(_CRD))
    except Conflict:
        pass  # installed by an earlier test; the cluster lives for the session
    loose: Api[LooseGadget] = Api(
        LooseGadget, client=client, namespace=tmp_namespace_name
    )
    with anyio.fail_after(_TIMEOUT):
        while True:
            try:
                await loose.list()
                break
            except (NotFound, TooManyRequests):  # not served yet / storage starting
                await anyio.sleep(0.2)
    await loose.create(
        LooseGadget(metadata=ObjectMetadata(name="good"), spec={"replicas": 1})
    )
    await loose.create(
        LooseGadget(metadata=ObjectMetadata(name="bad"), spec={"replicas": "three"})
    )
    return Api(Gadget, client=client, namespace=tmp_namespace_name), loose


async def test_watch_include_goes_on_past_invalid_objects(
    gadgets: tuple[Api[Gadget], Api[LooseGadget]],
) -> None:
    api, loose = gadgets
    initial: dict[str | None, WatchEvent[Gadget] | InvalidWatchEvent] = {}
    deleted: WatchEvent[Gadget] | InvalidWatchEvent | None = None
    synced = False

    with anyio.fail_after(_TIMEOUT):
        async for event in api.watch(
            send_initial_events=True, invalid=InvalidObjects.INCLUDE
        ):
            if event.is_initial_events_end:
                synced = True
                # `api.delete` would parse the deleted object with `Gadget` too.
                await loose.delete("bad")
            elif not synced and event.type is not EventType.BOOKMARK:
                initial[event.object.metadata.name] = event
            elif event.type is EventType.DELETED:
                deleted = event
                break

    good = initial["good"]
    assert isinstance(good, WatchEvent) and isinstance(good.object, Gadget)
    assert good.object.spec is not None and good.object.spec.replicas == 1

    bad = initial["bad"]
    assert isinstance(bad, InvalidWatchEvent)
    assert bad.type is EventType.ADDED
    assert bad.object.raw["spec"] == {"replicas": "three"}
    assert "replicas" in str(bad.object.error)

    # A DELETED event for an invalid object still says which object went away.
    assert isinstance(deleted, InvalidWatchEvent)
    assert deleted.object.metadata.name == "bad"
    assert deleted.object.metadata.uid == bad.object.metadata.uid


async def test_watch_raises_on_invalid_objects_by_default(
    gadgets: tuple[Api[Gadget], Api[LooseGadget]],
) -> None:
    api, _ = gadgets
    with pytest.raises(ValidationError), anyio.fail_after(_TIMEOUT):
        async for _ in api.watch(send_initial_events=True):
            pass


async def test_list_include_keeps_invalid_objects_apart(
    gadgets: tuple[Api[Gadget], Api[LooseGadget]],
) -> None:
    api, _ = gadgets

    result = await api.list(invalid=InvalidObjects.INCLUDE)

    assert [gadget.metadata.name for gadget in result.items] == ["good"]
    assert [obj.metadata.name for obj in result.invalid] == ["bad"]
    assert result.metadata.resource_version
    with pytest.raises(ValidationError):
        await api.list()


async def test_initial_events_end_bookmark_is_a_resume_point(
    client: BaseClient, tmp_namespace_name: str
) -> None:
    api: Api[ConfigMap] = Api(ConfigMap, client=client, namespace=tmp_namespace_name)
    for name in ("cm-1", "cm-2"):
        await api.create(ConfigMap(metadata=ObjectMetadata(name=name)))

    added: set[str | None] = set()
    resume_from: str | None = None
    with anyio.fail_after(_TIMEOUT):
        async for event in api.watch(send_initial_events=True):
            if event.is_initial_events_end:
                resume_from = event.object.metadata.resource_version
                break
            if event.type is EventType.ADDED:
                added.add(event.object.metadata.name)
    assert {"cm-1", "cm-2"} <= added
    assert resume_from

    # Resuming from the bookmark delivers only what changed after the snapshot.
    await api.create(ConfigMap(metadata=ObjectMetadata(name="cm-3")))
    with anyio.fail_after(_TIMEOUT):
        async for event in api.watch(resource_version=resume_from):
            assert event.type is EventType.ADDED
            assert event.object.metadata.name == "cm-3"
            break
