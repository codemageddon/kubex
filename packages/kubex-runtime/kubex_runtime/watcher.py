"""A stream of the objects of a kind: the current ones, then their changes.

`watcher()` gets the current objects (as a streaming list by default, or with
paged list requests), then watches them from the version they are current at,
gets them again when that version expired (410 Gone), and retries failures with
a backoff instead of ending. It also says how far the watch has got
(`InitDone`'s version, `Bookmark`), which a store uses to know which writes it
has seen.
"""

from __future__ import annotations

import logging
import math
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from enum import Enum
from types import EllipsisType
from typing import TYPE_CHECKING, Generic, TypeAlias, TypeVar, cast

import anyio

from kubex.core.exceptions import (
    Gone,
    KubexClientException,
    KubexTimeoutError,
    UnprocessableEntity,
)
from kubex.core.invalid_object import InvalidObject
from kubex.core.params import InvalidObjects, TimeoutTypes
from kubex.core.watch_event import EventType, InvalidWatchEvent, WatchEvent
from kubex_core.models.base_entity import BaseEntity

from ._closing import closing
from .backoff import Backoff, default_backoff

if TYPE_CHECKING:
    from kubex.api import Api

logger = logging.getLogger(__name__)

K = TypeVar("K", bound=BaseEntity)

# how long past its server-side timeout a watch may run before it is taken for a
# dead connection (the deadline is set when the watch opens, events do not move it)
_STALL_MARGIN = 30.0


@dataclass(frozen=True)
class Init:
    """A (re-)sync starts: the objects that follow replace the known ones."""


@dataclass(frozen=True)
class InitApply(Generic[K]):
    """An object of the ongoing (re-)sync."""

    obj: K


@dataclass(frozen=True)
class InitDone:
    """The (re-)sync ended: every current object has been sent.

    `resource_version` is the list's, or that of the bookmark that ends a
    streaming list; None when the source does not say.
    """

    resource_version: str | None = None


@dataclass(frozen=True)
class Apply(Generic[K]):
    """An object was added or modified."""

    obj: K


@dataclass(frozen=True)
class Delete(Generic[K]):
    """An object was deleted; `obj` is its last state."""

    obj: K


@dataclass(frozen=True)
class Bookmark:
    """The watch has sent every change up to `resource_version`."""

    resource_version: str


Event: TypeAlias = Init | InitApply[K] | InitDone | Apply[K] | Delete[K] | Bookmark


class InitialListStrategy(str, Enum):
    """How the watcher gets the current objects, at the start and on a re-list.

    Either way the stream is the same: `Init`, an `InitApply` per object,
    `InitDone`, then the changes.
    """

    LIST_WATCH = "list_watch"
    """Paged list requests, then a watch from the list's resourceVersion."""

    STREAMING_LIST = "streaming_list"
    """One watch with `sendInitialEvents`: the server sends the current objects,
    then a bookmark that ends them, then the changes. Lighter on the API server
    than paging a large list, but it needs the server's `WatchList` feature; a
    server without it rejects the watch with 422 Unprocessable Entity, which is
    retried after the backoff like any other failure."""

    STREAMING_LIST_WITH_FALLBACK = "streaming_list_with_fallback"
    """`STREAMING_LIST`, switching to `LIST_WATCH` for the rest of the
    watcher's life if the server rejects the streaming list with 422, or ends
    the stream before the bookmark that ends the initial events (a server that
    ignores `sendInitialEvents`). The default."""


@dataclass(frozen=True)
class WatcherConfig:
    """What to watch and how.

    `timeout` is the server-side timeout of one watch request (the server ends the
    stream after it, and the watcher reopens it); 290 s by default, under the
    API server's default of 300 s. A watch that has not ended 30 s after
    that is taken for a dead connection: it is reported to `on_error` as a
    `KubexTimeoutError` and retried after the backoff, like any other failure.
    `request_timeout` is the
    HTTP timeout of the list requests, `watch_request_timeout` the one of the
    watch requests; Ellipsis keeps the client's defaults.
    `initial_list_strategy` picks paged lists or a streaming list (see
    `InitialListStrategy`); None is `STREAMING_LIST_WITH_FALLBACK`, or
    `LIST_WATCH` without `bookmarks`: a streaming list ends with a bookmark, so
    it needs them.
    """

    label_selector: str | None = None
    field_selector: str | None = None
    timeout: int | None = 290
    page_size: int | None = 500
    bookmarks: bool = True
    request_timeout: TimeoutTypes | EllipsisType = ...
    watch_request_timeout: TimeoutTypes | EllipsisType = ...
    initial_list_strategy: InitialListStrategy | None = None

    def __post_init__(self) -> None:
        if (
            self.initial_list_strategy not in (None, InitialListStrategy.LIST_WATCH)
            and not self.bookmarks
        ):
            raise ValueError("a streaming list needs bookmarks=True")


ErrorHandler = Callable[[Exception], None]
RecoveryHandler = Callable[[], None]


def watcher(
    api: Api[K],
    config: WatcherConfig | None = None,
    *,
    backoff: Backoff | None = None,
    on_error: ErrorHandler | None = None,
    on_recovered: RecoveryHandler | None = None,
) -> AsyncIterator[Event[K]]:
    """Watches the objects of `api`: the current ones, then their changes.

    A failed request is retried after `backoff` (`default_backoff()` if None)
    and reported to `on_error`; the stream only ends with an exception when the
    backoff gives up. The stream resets `backoff` when it starts, so one given
    to several watchers in turn carries no failures over. `on_recovered` is
    called on the first success after a failure: once a whole (re-)list succeeds
    (a page alone is not enough), or a watch delivers an event or ends on its
    server timeout. The stream carries no errors: only these hooks tell. Objects
    that do not fit the model are logged and skipped.

    `InitDone` carries the version the objects are current at (the list's, or
    that of the bookmark ending a streaming list), and a `Bookmark` each of the
    server's bookmarks after it: the watch has sent every change up to that
    version.
    """
    return _Watcher(
        api,
        config or WatcherConfig(),
        backoff or default_backoff(),
        on_error,
        on_recovered,
    )()


class _Watcher(Generic[K]):
    def __init__(
        self,
        api: Api[K],
        config: WatcherConfig,
        backoff: Backoff,
        on_error: ErrorHandler | None,
        on_recovered: RecoveryHandler | None,
    ) -> None:
        self._api = api
        self._config = config
        self._backoff = backoff
        self._on_error = on_error
        self._on_recovered = on_recovered
        self._strategy = config.initial_list_strategy or (
            InitialListStrategy.STREAMING_LIST_WITH_FALLBACK
            if config.bookmarks
            else InitialListStrategy.LIST_WATCH
        )
        self._resource_version: str | None = None
        self._failed = False

    async def __call__(self) -> AsyncIterator[Event[K]]:
        self._backoff.reset()
        while True:
            # until InitDone, a failure starts the (re-)list over
            listing = self._resource_version is None
            try:
                if listing and self._strategy is InitialListStrategy.LIST_WATCH:
                    async with closing(self._list()) as events:
                        async for event in events:
                            yield event
                    listing = False
                async with closing(self._watch(streaming_list=listing)) as events:
                    async for event in events:
                        if isinstance(event, InitDone):
                            listing = False
                        yield event
                if listing:
                    if (
                        self._strategy
                        is InitialListStrategy.STREAMING_LIST_WITH_FALLBACK
                    ):
                        logger.warning(
                            "the streaming list ended before its initial events"
                            " did (does the server ignore sendInitialEvents?),"
                            " using paged lists"
                        )
                        self._strategy = InitialListStrategy.LIST_WATCH
                        continue
                    raise KubexClientException(
                        "the watch ended before its initial events did"
                    )
                # the server ended the stream on its timeout
                self._succeeded()
            except Exception as ex:
                if (
                    listing
                    and isinstance(ex, UnprocessableEntity)
                    and self._strategy
                    is InitialListStrategy.STREAMING_LIST_WITH_FALLBACK
                ):
                    logger.info("streaming list rejected, using paged lists: %s", ex)
                    self._strategy = InitialListStrategy.LIST_WATCH
                    continue
                if isinstance(ex, Gone) and not listing:
                    # the watch resumed from a compacted version: routine
                    logger.info("resource version expired, re-listing")
                    self._resource_version = None
                    continue
                # a list that keeps expiring (its continue token) backs off
                self._failed = True
                delay = self._backoff.next()
                if self._on_error is not None:
                    self._on_error(ex)
                if delay is None:
                    raise
                logger.warning("watching failed, retrying in %.2fs: %r", delay, ex)
                await anyio.sleep(delay)

    async def _list(self) -> AsyncIterator[Event[K]]:
        yield Init()
        continue_token: str | None = None
        while True:
            page = await self._api.list(
                label_selector=self._config.label_selector,
                field_selector=self._config.field_selector,
                limit=self._config.page_size,
                continue_token=continue_token,
                request_timeout=self._config.request_timeout,
                invalid=InvalidObjects.INCLUDE,
            )
            for invalid in page.invalid:
                self._log_invalid(invalid)
            for obj in page.items:
                yield InitApply(obj)
            continue_token = page.metadata.continue_
            if not continue_token:
                self._resource_version = page.metadata.resource_version
                break
        # only the whole list is a success: a retry starts again from page 1, so
        # a page that succeeds would reset the backoff of one that keeps failing
        self._succeeded()
        yield InitDone(self._resource_version)

    async def _watch(self, *, streaming_list: bool) -> AsyncIterator[Event[K]]:
        """Watches from the resume version; with `streaming_list`, starts with
        the current objects, up to the bookmark that ends them."""
        stream = self._api.watch(
            label_selector=self._config.label_selector,
            field_selector=self._config.field_selector,
            allow_bookmarks=self._config.bookmarks,
            send_initial_events=True if streaming_list else None,
            resource_version=self._resource_version,
            timeout_seconds=self._config.timeout,
            request_timeout=self._config.watch_request_timeout,
            invalid=InvalidObjects.INCLUDE,
        )
        deadline = math.inf
        if self._config.timeout is not None:
            deadline = anyio.current_time() + self._config.timeout + _STALL_MARGIN
        async with closing(stream):
            if streaming_list:
                event = await self._next(stream, deadline)
                # sent once the server took the watch: when it rejects it, the
                # fallback list sends its own
                yield Init()
                while event is not None and not event.is_initial_events_end:
                    if isinstance(event, InvalidWatchEvent):
                        self._log_invalid(event.object)
                    elif event.type in (EventType.ADDED, EventType.MODIFIED):
                        yield InitApply(cast(K, event.object))
                    # other bookmarks are checkpoints; the server sends no
                    # DELETED among the initial events
                    event = await self._next(stream, deadline)
                if event is None:
                    return  # before the initial events did: the caller decides
                self._resource_version = event.object.metadata.resource_version
                self._succeeded()
                yield InitDone(self._resource_version)
            while (event := await self._next(stream, deadline)) is not None:
                self._resource_version = (
                    event.object.metadata.resource_version or self._resource_version
                )
                self._succeeded()
                if isinstance(event, InvalidWatchEvent):
                    self._log_invalid(event.object)
                    continue
                match event.type:
                    case EventType.ADDED | EventType.MODIFIED:
                        yield Apply(cast(K, event.object))
                    case EventType.DELETED:
                        yield Delete(cast(K, event.object))
                    case EventType.BOOKMARK:
                        if version := event.object.metadata.resource_version:
                            yield Bookmark(version)

    async def _next(
        self,
        stream: AsyncIterator[WatchEvent[K] | InvalidWatchEvent],
        deadline: float,
    ) -> WatchEvent[K] | InvalidWatchEvent | None:
        """The next event of `stream`, or None once it ended.

        A coroutine of its own, so its cancel scope never spans a yield (it
        would cover the consumer).
        """
        with anyio.move_on_at(deadline):
            try:
                return await anext(stream)
            except StopAsyncIteration:
                return None
        raise KubexTimeoutError(
            f"the watch did not end {_STALL_MARGIN:.0f}s after its "
            f"{self._config.timeout}s timeout"
        )

    def _succeeded(self) -> None:
        self._backoff.reset()
        if self._failed:
            self._failed = False
            if self._on_recovered is not None:
                self._on_recovered()

    def _log_invalid(self, invalid: InvalidObject) -> None:
        metadata = invalid.metadata
        logger.error(
            "skipping %s/%s, which does not fit its model: %s",
            metadata.namespace,
            metadata.name,
            invalid.error,
        )
