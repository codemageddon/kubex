"""The controller: what triggers its reconciles, and running them."""

from __future__ import annotations

import logging
import threading
from collections.abc import (
    AsyncGenerator,
    AsyncIterable,
    AsyncIterator,
    Callable,
    Iterable,
)
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, Generic, TypeVar

import anyio
from anyio.streams.memory import MemoryObjectReceiveStream

from kubex.core.exception_groups import raise_single
from kubex_core.models.base_entity import BaseEntity
from kubex_core.models.resource_config import Scope

from ..object_ref import ObjectRef
from ..reflector import (
    ReflectHandle,
    SharedReflector,
    Store,
    SubscriberBuffer,
    Writer,
    reflector,
)
from ..watcher import WatcherConfig, watcher
from ._applier import _Applier
from ._triggers import (
    _bulk_triggers,
    _mapped_triggers,
    _ref_triggers,
    _self_triggers,
    _subscription,
    _watched_triggers,
)
from ._types import (
    Adapter,
    ControllerConfig,
    ErrorPolicyFn,
    Mapper,
    ReconcileFn,
    ReconcileRequest,
    ReconcileResult,
)

if TYPE_CHECKING:
    from kubex.api import Api

logger = logging.getLogger("kubex_runtime.controller")

K = TypeVar("K", bound=BaseEntity)
R = TypeVar("R", bound=BaseEntity)
C = TypeVar("C")

# results that may wait for the reader of `running()` before reconciles pause
_RESULTS_BUFFER = 128

_Triggers = Callable[[], AsyncIterator[ReconcileRequest]]
# subscribes to a controller's own watch and starts it
_OwnWatch = Callable[[], tuple[ReflectHandle[K], AsyncIterator[Any]]]


class Controller(Generic[K]):
    """Reconciles the objects of `model`.

    Built either on its own watch of `api`, or with `for_shared` on a
    `SharedReflector` (`for_shared_stream` takes any stream of its objects and
    the store it reads). Triggers are added with the builder methods; `run` or
    `running` reconciles, once: a controller keeps its store and the streams it
    was given, so to run again (after losing a leader election, say) build a new
    one.

    `buffer` is how the controller's own watch buffers changes for it (see
    `Writer.subscribe`).
    """

    def __init__(
        self,
        model: type[K],
        api: Api[K],
        watcher_config: WatcherConfig | None = None,
        *,
        buffer: SubscriberBuffer | None = None,
    ) -> None:
        writer: Writer[K] = Writer()

        def own_watch() -> tuple[ReflectHandle[K], AsyncIterator[Any]]:
            # subscribed before the watch starts, so it misses nothing; reading
            # the store's subscription, not the watch, means a trigger only
            # comes once the store has the object (a re-list is applied at its
            # end)
            subscription = writer.subscribe(buffer)
            return subscription, reflector(writer, watcher(api, watcher_config))

        self._setup(model, writer.as_reader(), own_watch)

    def _setup(
        self,
        model: type[K],
        store: Store[K],
        own_watch: _OwnWatch[K] | None = None,
    ) -> None:
        self._model = model
        self._store = store
        self._config = ControllerConfig()
        # factories, called when the controller runs
        self._triggers: list[_Triggers] = []
        self._started = False
        self._start_lock = threading.Lock()
        self._waits_for: list[Store[Any]] = []
        self._own_watch = own_watch

    @classmethod
    def _reading(cls, model: type[K], store: Store[K]) -> Controller[K]:
        """A controller with no watch of its own, reading `store`."""
        controller = cls.__new__(cls)
        controller._setup(model, store)
        return controller

    @classmethod
    def for_shared(
        cls,
        model: type[K],
        shared: SharedReflector[K],
        *,
        buffer: SubscriberBuffer | None = None,
        adapt: Adapter[K] | None = None,
    ) -> Controller[K]:
        """A controller of the objects of `shared`, reading its store.

        It subscribes when it starts running, with `buffer` (a `MergedBuffer()`
        by default: the controller reads the latest state from the store
        anyway), and closes the subscription when it stops, so a controller
        that is built but never run never holds up the watch. `adapt` wraps the
        subscription, e.g. `lambda s: predicate_filter(s, generation)` to skip
        status-only changes (see `generation` for what else it skips).
        """
        controller = cls._reading(model, shared.store)
        controller._triggers.append(
            lambda: _self_triggers(_subscription(shared, buffer, adapt))
        )
        return controller

    @classmethod
    def for_shared_stream(
        cls, model: type[K], stream: AsyncIterable[K], store: Store[K]
    ) -> Controller[K]:
        """A controller of the objects of a shared reflector: `stream` is a
        subscription to its writer (or an adapter of one), `store` its reader.

        The controller closes `stream` when it stops.
        """
        controller = cls._reading(model, store)
        controller._triggers.append(lambda: _self_triggers(stream))
        return controller

    @property
    def store(self) -> Store[K]:
        return self._store

    def with_config(self, config: ControllerConfig) -> Controller[K]:
        self._config = config
        return self

    def waits_for(self, *stores: Store[Any]) -> Controller[K]:
        """Holds every reconcile until `stores` are ready too, not just the
        controller's own: the stores the reconcile function reads, such as the
        cache of the objects it owns. Reconciled before that store has listed,
        an owner would find no children and create them again. An object is
        also held until these stores have seen the writes recorded for it
        (`Store.wrote`).
        """
        self._waits_for.extend(stores)
        return self

    def owns(
        self, model: type[R], api: Api[R], watcher_config: WatcherConfig | None = None
    ) -> Controller[K]:
        """Reconciles the controlling owner of every changed object of `api`,
        and of every one a re-list no longer finds (deleted while the watch was
        down).
        """
        del model  # the owner references say everything
        self._triggers.append(
            lambda: _watched_triggers(
                watcher(api, watcher_config), self._controlling_owner
            )
        )
        return self

    def owns_shared(
        self,
        shared: SharedReflector[R],
        *,
        buffer: SubscriberBuffer | None = None,
        adapt: Adapter[R] | None = None,
    ) -> Controller[K]:
        """Reconciles the controlling owner of every changed object of
        `shared`, and waits for its store; subscribes as `for_shared` does.
        """
        return self.watches_shared(
            shared, self._controlling_owner, buffer=buffer, adapt=adapt
        )

    def owns_shared_stream(self, stream: AsyncIterable[R]) -> Controller[K]:
        return self.watches_shared_stream(stream, self._controlling_owner)

    def watches(
        self,
        model: type[R],
        api: Api[R],
        mapper: Mapper[R],
        watcher_config: WatcherConfig | None = None,
    ) -> Controller[K]:
        """Reconciles the objects `mapper` returns for every changed object of
        `api`, and for every one a re-list no longer finds (with its last state).
        """
        del model
        self._triggers.append(
            lambda: _watched_triggers(watcher(api, watcher_config), mapper)
        )
        return self

    def watches_shared(
        self,
        shared: SharedReflector[R],
        mapper: Mapper[R],
        *,
        buffer: SubscriberBuffer | None = None,
        adapt: Adapter[R] | None = None,
    ) -> Controller[K]:
        """Reconciles the objects `mapper` returns for every changed object of
        `shared`, and waits for its store, which the reconcile function
        presumably reads; subscribes as `for_shared` does.
        """
        self._triggers.append(
            lambda: _mapped_triggers(_subscription(shared, buffer, adapt), mapper)
        )
        return self.waits_for(shared.store)

    def watches_shared_stream(
        self, stream: AsyncIterable[R], mapper: Mapper[R]
    ) -> Controller[K]:
        self._triggers.append(lambda: _mapped_triggers(stream, mapper))
        return self

    def reconcile_on(self, stream: AsyncIterable[ObjectRef]) -> Controller[K]:
        """Reconciles every object `stream` refers to."""
        self._triggers.append(lambda: _ref_triggers(stream))
        return self

    def reconcile_all_on(self, stream: AsyncIterable[Any]) -> Controller[K]:
        """Reconciles every object of the store on every item of `stream`."""
        self._triggers.append(lambda: _bulk_triggers(stream, self._store))
        return self

    @asynccontextmanager
    async def running(
        self,
        reconcile: ReconcileFn[K, C],
        error_policy: ErrorPolicyFn[K, C],
        context: C,
    ) -> AsyncGenerator[MemoryObjectReceiveStream[ReconcileResult], None]:
        """Reconciles while the block runs, handing out the result of every
        reconcile.

        Nothing is reconciled before the store, and every store given to
        `waits_for`, is ready; triggers that come earlier wait. A trigger for an object
        that is not in the store is dropped. One object is never reconciled twice
        at once: a trigger arriving meanwhile runs right after. An object one of
        those stores has a write recorded for (`Store.wrote`) is held until that
        store has seen it, without taking a place under `concurrency`: reconciled
        in between, an owner would not find the child it just created, and create
        it again. A hold that lasts 60 s is logged. Read the results:
        once 128 of them wait, reconciles pause until they are read. Leaving the
        block cancels the reconciles in flight.

        The watches the controller runs itself (its own, and those of `owns` and
        `watches`) retry every failure with the default backoff (`default_backoff()`), which
        never gives up. A trigger stream that fails, such as one given to
        `reconcile_on` or `for_shared_stream`, ends the block with its error.
        For a bounded backoff, or `on_error`/`on_recovered`, watch through a
        `SharedReflector` (`for_shared`, `owns_shared`, `watches_shared`).

        A controller runs once: entering `running` (or `run`) again, during or
        after a run (in any thread), raises `RuntimeError`.
        """
        with self._start_lock:
            if self._started:
                raise RuntimeError(
                    "a Controller runs once: build a new one to run again"
                )
            self._started = True
        results, receiver = anyio.create_memory_object_stream[ReconcileResult](
            _RESULTS_BUFFER
        )
        applier = _Applier(
            self._model.__name__,
            self._store,
            self._waits_for,
            self._config,
            reconcile,
            error_policy,
            context,
            results,
        )
        own_watch: AsyncIterator[Any] | None = None
        triggers = [factory() for factory in self._triggers]
        if self._own_watch is not None:
            subscription, own_watch = self._own_watch()
            triggers.append(_self_triggers(subscription))
        try:
            # one task group for everything, so a failure comes out as itself
            async with anyio.create_task_group() as group:
                applier.start(group, triggers, own_watch)
                try:
                    yield receiver
                finally:
                    group.cancel_scope.cancel()
        except BaseExceptionGroup as errors:
            raise_single(errors)
            raise
        finally:
            results.close()
            receiver.close()

    async def run(
        self,
        reconcile: ReconcileFn[K, C],
        error_policy: ErrorPolicyFn[K, C],
        context: C,
    ) -> None:
        """Reconciles until cancelled, logging every failed reconcile.

        `running` without the results; start it in a task group to run several
        controllers together.
        """
        async with self.running(reconcile, error_policy, context) as results:
            async for result in results:
                if result.error is not None:
                    logger.error(
                        "reconciling %s failed (%s)",
                        result.obj_ref,
                        result.reason,
                        exc_info=result.error,
                    )

    def _controlling_owner(self, obj: BaseEntity) -> Iterable[ObjectRef]:
        # an owner is in its dependent's namespace, or cluster-scoped
        namespaced = self._model.__RESOURCE_CONFIG__.scope is Scope.NAMESPACE
        namespace = obj.metadata.namespace if namespaced else None
        for owner in obj.metadata.owner_references or []:
            if not owner.controller:
                continue
            ref = ObjectRef.from_owner(owner, namespace)
            if ref.is_kind_of(self._model):
                yield ref
