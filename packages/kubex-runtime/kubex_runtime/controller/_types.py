"""What a controller is given and hands out: the reconcile function's result,
why an object is reconciled, and the controller's settings."""

from __future__ import annotations

from collections.abc import AsyncIterable, Awaitable, Callable, Iterable
from dataclasses import dataclass
from typing import TypeVar

from kubex_core.models.base_entity import BaseEntity

from ..object_ref import ObjectRef

K = TypeVar("K", bound=BaseEntity)
R = TypeVar("R", bound=BaseEntity)
C = TypeVar("C")


@dataclass(frozen=True)
class Action:
    """What to do with an object after reconciling it.

    `requeue_after` is the delay in seconds before the next reconcile, None to
    wait for a trigger.
    """

    requeue_after: float | None = None

    @classmethod
    def requeue(cls, seconds: float) -> Action:
        return cls(requeue_after=seconds)

    @classmethod
    def await_change(cls) -> Action:
        return cls()


@dataclass(frozen=True)
class ReconcileReason:
    """Why an object is reconciled."""

    name: str
    related: ObjectRef | None = None

    @classmethod
    def related_object_updated(cls, related: ObjectRef) -> ReconcileReason:
        return cls("related object updated", related)

    def __str__(self) -> str:
        if self.related is not None:
            return f"{self.name}: {self.related}"
        return self.name


OBJECT_UPDATED = ReconcileReason("object updated")
RECONCILER_REQUESTED_RETRY = ReconcileReason("reconciler requested retry")
ERROR_POLICY_REQUESTED_RETRY = ReconcileReason("error policy requested retry")
BULK_RECONCILE = ReconcileReason("bulk reconcile")
UNKNOWN = ReconcileReason("unknown")


@dataclass(frozen=True)
class ReconcileRequest:
    obj_ref: ObjectRef
    reason: ReconcileReason = UNKNOWN


@dataclass(frozen=True)
class ReconcileResult:
    """The outcome of one reconcile: its action, or the error it raised."""

    obj_ref: ObjectRef
    reason: ReconcileReason
    action: Action | None = None
    error: Exception | None = None


@dataclass(frozen=True)
class ControllerConfig:
    """`debounce` delays every trigger by that many seconds, merging the triggers
    of one object that come within it; `concurrency` caps the reconciles running
    at once, 0 for no cap.
    """

    debounce: float = 0.0
    concurrency: int = 0


ReconcileFn = Callable[[K, C], Awaitable[Action]]
ErrorPolicyFn = Callable[[K, Exception, C], Action]
Mapper = Callable[[R], Iterable[ObjectRef]]
Adapter = Callable[[AsyncIterable[R]], AsyncIterable[R]]
