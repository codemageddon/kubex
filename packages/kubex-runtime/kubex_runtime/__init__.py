"""A controller runtime for kubex, modelled on kube-runtime (kube.rs).

- `watcher` gets the current objects of a kind (as a streaming list, or with
  paged lists) and watches their changes, as a stream of events;
- `reflector` keeps a `Store` of those objects up to date, and its `Writer` can be
  subscribed to so that several controllers share one watch, through a bounded
  queue (`BoundedBuffer`, the default) or one entry per object (`MergedBuffer`);
  `SharedReflector` (and `shared_reflector()`) bundles the watch, the store and
  the subscriptions for controllers;
- `Controller` calls a reconcile function for every object that changed, or
  whose related objects changed, and requeues it as the function asks; an
  object is held until its stores have seen the writes recorded for it
  (`Store.wrote`);
- `finalizer` runs cleanup before an object is deleted.

Everything runs on asyncio and trio, through anyio, and on free-threaded Python:
a store can be read from any thread, and a writer subscribed to and read from in
any thread's event loop (see the README).
"""

from .backoff import Backoff, ExponentialBackoff, default_backoff
from .controller import (
    Action,
    Controller,
    ControllerConfig,
    ReconcileReason,
    ReconcileRequest,
    ReconcileResult,
)
from .finalizer import (
    Apply as FinalizerApply,
    Cleanup as FinalizerCleanup,
    FinalizerError,
    FinalizerEvent,
    finalizer,
)
from .object_ref import ObjectRef
from .reflector import (
    BoundedBuffer,
    MergedBuffer,
    ReflectHandle,
    SharedReflector,
    Store,
    SubscriberBuffer,
    Writer,
    reflector,
    shared_reflector,
    store,
)
from .streams import (
    applied_objects,
    generation,
    predicate_filter,
    resource_version,
    touched_objects,
)
from .watcher import (
    Apply,
    Bookmark,
    Delete,
    Event,
    Init,
    InitApply,
    InitDone,
    InitialListStrategy,
    WatcherConfig,
    watcher,
)

__all__ = [
    "Action",
    "Apply",
    "Backoff",
    "Bookmark",
    "BoundedBuffer",
    "Controller",
    "ControllerConfig",
    "Delete",
    "Event",
    "ExponentialBackoff",
    "FinalizerApply",
    "FinalizerCleanup",
    "FinalizerError",
    "FinalizerEvent",
    "Init",
    "InitApply",
    "InitDone",
    "InitialListStrategy",
    "MergedBuffer",
    "ObjectRef",
    "ReconcileReason",
    "ReconcileRequest",
    "ReconcileResult",
    "ReflectHandle",
    "SharedReflector",
    "Store",
    "SubscriberBuffer",
    "WatcherConfig",
    "Writer",
    "applied_objects",
    "default_backoff",
    "finalizer",
    "generation",
    "predicate_filter",
    "reflector",
    "resource_version",
    "shared_reflector",
    "store",
    "touched_objects",
    "watcher",
]
