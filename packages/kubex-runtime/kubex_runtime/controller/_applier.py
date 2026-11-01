"""Schedules a controller's reconciles and runs them."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import suppress
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

import anyio
from anyio.abc import TaskGroup
from anyio.streams.memory import MemoryObjectSendStream

from kubex_core.models.base_entity import BaseEntity

from .._closing import closing
from ..object_ref import ObjectRef
from ..reflector import Store
from ..scheduler import Scheduler
from ._types import (
    ERROR_POLICY_REQUESTED_RETRY,
    RECONCILER_REQUESTED_RETRY,
    ControllerConfig,
    ErrorPolicyFn,
    ReconcileFn,
    ReconcileReason,
    ReconcileRequest,
    ReconcileResult,
)

logger = logging.getLogger("kubex_runtime.controller")

K = TypeVar("K", bound=BaseEntity)
C = TypeVar("C")

# seconds a controller waits for its stores before warning that it still does
_READY_WARNING_AFTER = 60.0

# seconds a controller holds an object for the writes recorded for it before
# warning that it still does
_UNSEEN_WRITES_WARNING_AFTER = 60.0


async def _drain(stream: AsyncIterator[Any]) -> None:
    async with closing(stream) as events:
        async for _ in events:
            pass


@dataclass(frozen=True)
class _Hold:
    """An object held until its stores have seen what was written for it."""

    uid: str
    # the trigger that came first, scheduled again once they have
    reason: ReconcileReason
    # its wait, cancelled when the hold is dropped
    scope: anyio.CancelScope


class _Applier(Generic[K, C]):
    def __init__(
        self,
        name: str,
        store: Store[K],
        waits_for: list[Store[Any]],
        config: ControllerConfig,
        reconcile: ReconcileFn[K, C],
        error_policy: ErrorPolicyFn[K, C],
        context: C,
        results: MemoryObjectSendStream[ReconcileResult],
    ) -> None:
        self._name = name
        self._store = store
        # a copy: stores added to the controller after it started have no effect
        self._stores = [store, *waits_for]
        self._reconcile = reconcile
        self._error_policy = error_policy
        self._context = context
        self._results = results
        self._scheduler: Scheduler[ObjectRef, ReconcileReason] = Scheduler(
            debounce=config.debounce
        )
        self._limit = (
            anyio.Semaphore(config.concurrency) if config.concurrency > 0 else None
        )
        self._running: set[ObjectRef] = set()
        # triggers that came while their object was being reconciled
        self._held: dict[ObjectRef, ReconcileReason] = {}
        # objects held until their stores have seen what was written for them
        self._unseen_writes: dict[ObjectRef, _Hold] = {}

    def start(
        self,
        group: TaskGroup,
        triggers: list[AsyncIterator[ReconcileRequest]],
        own_watch: AsyncIterator[Any] | None,
    ) -> None:
        if own_watch is not None:
            group.start_soon(_drain, own_watch)
        for trigger in triggers:
            group.start_soon(self._feed, trigger)
        group.start_soon(self._dispatch, group)

    async def _feed(self, triggers: AsyncIterator[ReconcileRequest]) -> None:
        async with closing(triggers) as requests:
            async for request in requests:
                self._scheduler.schedule(request.obj_ref, request.reason)

    async def _wait_until_ready(self) -> None:
        # a store, once ready, stays ready: waiting on each in turn is enough
        stores = self._stores
        with anyio.move_on_after(_READY_WARNING_AFTER):
            for store in stores:
                await store.wait_until_ready()
            return
        logger.warning(
            "%s controller: %d of %d stores not ready after %.0fs, reconciles "
            "wait for them (is every reflector running?)",
            self._name,
            sum(not store.is_ready() for store in stores),
            len(stores),
            _READY_WARNING_AFTER,
        )
        for store in stores:
            await store.wait_until_ready()

    async def _dispatch(self, group: TaskGroup) -> None:
        await self._wait_until_ready()
        while True:
            ref, reason = await self._scheduler.next()
            if ref in self._running:
                self._held.setdefault(ref, reason)
                continue
            uid = self._uid_of(ref)
            if (hold := self._unseen_writes.get(ref)) is not None:
                if hold.uid == uid:
                    continue  # scheduled again once its stores have seen them
                # gone, or re-created under its name: those writes are not its
                hold.scope.cancel()
                del self._unseen_writes[ref]
            if uid is not None and (stores := self._stores_behind(uid)):
                hold = _Hold(uid, reason, anyio.CancelScope())
                self._unseen_writes[ref] = hold
                group.start_soon(self._await_writes, ref, hold, stores)
                continue
            if self._limit is not None:
                await self._limit.acquire()
            self._running.add(ref)
            group.start_soon(self._apply, ref, reason)

    def _uid_of(self, ref: ObjectRef) -> str | None:
        """The uid of the object `ref`, None when it is gone (`_apply` drops
        its trigger)."""
        obj = self._store.get(ref)
        return None if obj is None else obj.metadata.uid

    def _stores_behind(self, uid: str) -> list[Store[Any]]:
        """The stores that have not seen what was written for the object `uid`."""
        return [store for store in self._stores if store._pending(uid)]

    async def _await_writes(
        self, ref: ObjectRef, hold: _Hold, stores: list[Store[Any]]
    ) -> None:
        """Schedules `ref` again once `stores` have seen what was written for
        the object it is held for; `_dispatch` checks it again then. Ends
        when the hold is dropped."""
        with hold.scope:
            await self._writes_seen(ref, hold.uid, stores)
            # the hold may have been dropped after the wait ended (trio
            # delivers a cancellation at the next checkpoint only)
            if self._unseen_writes.get(ref) is hold:
                del self._unseen_writes[ref]
                self._scheduler.schedule(ref, hold.reason)

    async def _writes_seen(
        self, ref: ObjectRef, uid: str, stores: list[Store[Any]]
    ) -> None:
        # a store, once it has seen a write, has seen it for good
        with anyio.move_on_after(_UNSEEN_WRITES_WARNING_AFTER):
            for store in stores:
                await store._wait_for_uid(uid)
            return
        logger.warning(
            "%s controller: %s held %.0fs for its own writes, %d of %d "
            "stores have not seen them (is every reflector running, and "
            "does it watch what was written?)",
            self._name,
            ref,
            _UNSEEN_WRITES_WARNING_AFTER,
            sum(store._pending(uid) for store in stores),
            len(stores),
        )
        for store in stores:
            await store._wait_for_uid(uid)

    async def _apply(self, ref: ObjectRef, reason: ReconcileReason) -> None:
        try:
            obj = self._store.get(ref)
            if obj is None:
                logger.debug("%s is gone, not reconciling it", ref)
                return
            result = await self._call(ref, reason, obj)
            if result.action is not None and result.action.requeue_after is not None:
                retry = (
                    RECONCILER_REQUESTED_RETRY
                    if result.error is None
                    else ERROR_POLICY_REQUESTED_RETRY
                )
                self._scheduler.schedule(ref, retry, result.action.requeue_after)
            with suppress(anyio.BrokenResourceError, anyio.ClosedResourceError):
                await self._results.send(result)
        finally:
            self._running.discard(ref)
            if self._limit is not None:
                self._limit.release()
            if (held := self._held.pop(ref, None)) is not None:
                self._scheduler.schedule(ref, held)

    async def _call(
        self, ref: ObjectRef, reason: ReconcileReason, obj: K
    ) -> ReconcileResult:
        logger.debug("reconciling %s (%s)", ref, reason)
        try:
            action = await self._reconcile(obj, self._context)
        except Exception as error:
            try:
                action = self._error_policy(obj, error, self._context)
            except Exception:
                logger.exception("error policy failed for %s", ref)
                action = None
            return ReconcileResult(ref, reason, action, error)
        return ReconcileResult(ref, reason, action)
