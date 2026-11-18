"""A scripted stand-in for ``Api`` and helpers to build objects and events."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Generic, Sequence, TypeVar, cast

import anyio
import anyio.lowlevel

from kubex.api import Api
from kubex.core.exceptions import build_exception
from kubex.core.invalid_object import InvalidObject, ListWithInvalid
from kubex.core.watch_event import (
    INITIAL_EVENTS_END_ANNOTATION,
    InvalidWatchEvent,
    WatchEvent,
)
from kubex.k8s.v1_35.core.v1.config_map import ConfigMap
from kubex_core.models.base_entity import BaseEntity
from kubex_core.models.metadata import ListMetadata, ObjectMetadata, OwnerReference

K = TypeVar("K", bound=BaseEntity)


class _Block:
    """A watch step that waits forever (a quiet, open watch)."""


BLOCK = _Block()
"""In a watch script: stay open without sending anything."""


@dataclass
class Page:
    """One list response: ``continue_`` set means another page follows."""

    items: list[Any]
    continue_: str | None = None
    resource_version: str | None = None
    invalid: list[InvalidObject] = field(default_factory=list)


WatchStep = WatchEvent[Any] | InvalidWatchEvent | BaseException | _Block


class FakeApi(Generic[K]):
    """Serves scripted list pages and watch streams, recording every call.

    ``pages`` is consumed one entry per ``list()`` call (a ``Page`` or an
    exception to raise); ``watches`` one script per ``watch()`` call (a list of
    events, exceptions to raise, and ``BLOCK``); a watch with no script left
    blocks. A watch script that runs out ends the stream, as the server does on
    its timeout. ``list_delay`` makes every list call take that long.

    Without ``watch_list``, the fake is a server without the ``WatchList``
    feature: it rejects a streaming list with 422, before the watch opens and
    without using a script, and records it in ``rejected_watch_calls`` (not
    ``watch_calls``). The watcher's default strategy then falls back to lists.
    """

    def __init__(self, model: type[K], *, watch_list: bool = False) -> None:
        self.model = model
        self.watch_list = watch_list
        self.pages: deque[Page | BaseException] = deque()
        self.watches: deque[list[WatchStep]] = deque()
        self.list_calls: list[dict[str, Any]] = []
        self.watch_calls: list[dict[str, Any]] = []
        self.rejected_watch_calls: list[dict[str, Any]] = []
        self.open_watches = 0
        self.list_delay = 0.0

    def as_api(self) -> Api[K]:
        return cast("Api[K]", self)

    async def list(self, **kwargs: Any) -> ListWithInvalid[K]:
        self.list_calls.append(kwargs)
        if self.list_delay:
            await anyio.sleep(self.list_delay)
        else:
            await anyio.lowlevel.checkpoint()
        if not self.pages:
            raise AssertionError("unexpected list() call")
        page = self.pages.popleft()
        if isinstance(page, BaseException):
            raise page
        return ListWithInvalid[K](
            api_version="v1",
            kind="List",
            metadata=ListMetadata(
                continue_=page.continue_, resource_version=page.resource_version
            ),
            items=page.items,
            invalid=page.invalid,
        )

    def watch(self, **kwargs: Any) -> AsyncGenerator[Any, None]:
        if kwargs.get("send_initial_events") and not self.watch_list:
            self.rejected_watch_calls.append(kwargs)
            return self._rejected()
        self.watch_calls.append(kwargs)
        script = self.watches.popleft() if self.watches else [BLOCK]
        return self._watch(script)

    async def _rejected(self) -> AsyncGenerator[Any, None]:
        await anyio.lowlevel.checkpoint()
        raise build_exception(
            422,
            "sendInitialEvents is forbidden for watch unless the WatchList"
            " feature gate is enabled",
        )
        yield  # an async generator, as watch() returns

    async def _watch(self, script: Sequence[WatchStep]) -> AsyncGenerator[Any, None]:
        self.open_watches += 1
        try:
            for step in script:
                await anyio.lowlevel.checkpoint()
                if isinstance(step, BaseException):
                    raise step
                if isinstance(step, _Block):
                    await anyio.sleep_forever()
                yield step
        finally:
            self.open_watches -= 1


def cm(
    name: str,
    rv: str = "1",
    *,
    namespace: str = "ns",
    owners: list[OwnerReference] | None = None,
    **metadata: Any,
) -> ConfigMap:
    return ConfigMap(
        metadata=ObjectMetadata(
            name=name,
            namespace=namespace,
            resource_version=rv,
            owner_references=owners,
            **metadata,
        )
    )


def event(type_: str, obj: BaseEntity) -> WatchEvent[Any]:
    raw = {"type": type_, "object": obj.model_dump(by_alias=True, mode="json")}
    return WatchEvent(type(obj), raw)


def bookmark(rv: str, *, initial_events_end: bool = False) -> WatchEvent[Any]:
    metadata: dict[str, Any] = {"resourceVersion": rv}
    if initial_events_end:
        metadata["annotations"] = {INITIAL_EVENTS_END_ANNOTATION: "true"}
    raw = {"type": "BOOKMARK", "object": {"metadata": metadata}}
    return WatchEvent(ConfigMap, raw)


def owner(
    kind: str, name: str, *, api_version: str = "v1", controller: bool = True
) -> OwnerReference:
    return OwnerReference(
        api_version=api_version,
        kind=kind,
        name=name,
        uid=f"uid-{name}",
        controller=controller,
    )
