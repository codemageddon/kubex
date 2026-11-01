"""One watch and its store, shared by several consumers."""

from __future__ import annotations

import threading
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Generic, TypeVar

import anyio

from kubex.core.exception_groups import raise_single
from kubex_core.models.base_entity import BaseEntity

from .._closing import closing
from ..backoff import Backoff
from ..watcher import ErrorHandler, RecoveryHandler, WatcherConfig, watcher
from ._store import Store
from ._subscription import ReflectHandle, SubscriberBuffer
from ._writer import Writer, reflector

if TYPE_CHECKING:
    from kubex.api import Api

K = TypeVar("K", bound=BaseEntity)


class SharedReflector(Generic[K]):
    """One watch of a kind and the store it fills, for several consumers.

    `run()`, or `shared_reflector()`, runs the watch. Controllers use it through
    `Controller.for_shared`, `owns_shared` and `watches_shared`, which subscribe
    when the controller starts and wait for the store to be ready; `subscribe()`
    is for any other consumer.

    It outlives the controllers built on it: after a lost leader election, say,
    build new controllers on the same reflector and keep its store.

    The watch runs in the event loop of the API's client; the controllers and
    other consumers may run in other threads' event loops.
    """

    def __init__(
        self,
        api: Api[K],
        config: WatcherConfig | None = None,
        *,
        backoff: Backoff | None = None,
        on_error: ErrorHandler | None = None,
        on_recovered: RecoveryHandler | None = None,
    ) -> None:
        self._api = api
        self._config = config
        self._backoff = backoff
        self._on_error = on_error
        self._on_recovered = on_recovered
        self._writer: Writer[K] = Writer()
        self._running = False
        self._run_lock = threading.Lock()

    @property
    def store(self) -> Store[K]:
        return self._writer.as_reader()

    def subscribe(self, buffer: SubscriberBuffer | None = None) -> ReflectHandle[K]:
        """A subscription to the changes of the store, as `Writer.subscribe`."""
        return self._writer.subscribe(buffer)

    def wrote(self, obj: K, *, owner: BaseEntity) -> None:
        """Records a write in the store, as `Store.wrote`."""
        self._writer.as_reader().wrote(obj, owner=owner)

    def forget_writes(self) -> None:
        """Drops the writes recorded in the store, as `Store.forget_writes`."""
        self._writer.as_reader().forget_writes()

    async def run(self) -> None:
        """Runs the watch, keeping the store filled, until cancelled; raises the
        watcher's error if its backoff gives up.

        One run at a time: running it again while it runs (in any thread)
        raises `RuntimeError`. Run again after it ended, it lists anew and
        keeps its subscriptions, which first get the deletions a cancelled run
        had not delivered to them; its backoff starts over.
        """
        with self._run_lock:
            if self._running:
                raise RuntimeError("this SharedReflector is already running")
            self._running = True
        try:
            events = reflector(
                self._writer,
                watcher(
                    self._api,
                    self._config,
                    backoff=self._backoff,
                    on_error=self._on_error,
                    on_recovered=self._on_recovered,
                ),
            )
            async with closing(events) as stream:
                async for _ in stream:
                    pass
        finally:
            self._running = False


@asynccontextmanager
async def shared_reflector(
    api: Api[K],
    config: WatcherConfig | None = None,
    *,
    backoff: Backoff | None = None,
    on_error: ErrorHandler | None = None,
    on_recovered: RecoveryHandler | None = None,
) -> AsyncGenerator[SharedReflector[K], None]:
    """A `SharedReflector` whose watch runs while the block does.

    A watcher that gives up ends the block with its error, cancelling what the
    block runs; leaving the block stops the watch.
    """
    shared = SharedReflector(
        api, config, backoff=backoff, on_error=on_error, on_recovered=on_recovered
    )
    try:
        async with anyio.create_task_group() as group:
            group.start_soon(shared.run)
            try:
                yield shared
            finally:
                group.cancel_scope.cancel()
    except BaseExceptionGroup as errors:
        raise_single(errors)
        raise
