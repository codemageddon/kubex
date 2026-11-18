"""Runs a reconcile function for the objects of a kind.

A controller gathers triggers -- changes of its objects, of the objects they own
or watch, or any stream of references -- into a scheduler, and calls the
reconcile function with the latest state of each triggered object from its store.
"""

from ._controller import Controller
from ._types import (
    BULK_RECONCILE,
    ERROR_POLICY_REQUESTED_RETRY,
    OBJECT_UPDATED,
    RECONCILER_REQUESTED_RETRY,
    UNKNOWN,
    Action,
    Adapter,
    ControllerConfig,
    ErrorPolicyFn,
    Mapper,
    ReconcileFn,
    ReconcileReason,
    ReconcileRequest,
    ReconcileResult,
)

__all__ = [
    "BULK_RECONCILE",
    "ERROR_POLICY_REQUESTED_RETRY",
    "OBJECT_UPDATED",
    "RECONCILER_REQUESTED_RETRY",
    "UNKNOWN",
    "Action",
    "Adapter",
    "Controller",
    "ControllerConfig",
    "ErrorPolicyFn",
    "Mapper",
    "ReconcileFn",
    "ReconcileReason",
    "ReconcileRequest",
    "ReconcileResult",
]
