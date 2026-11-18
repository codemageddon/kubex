"""Cleanup before deletion with a finalizer."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Generic, Protocol, TypeAlias, TypeVar

from kubex.core.exceptions import NotFound
from kubex.core.patch import JsonPatch
from kubex_core.models.base_entity import BaseEntity
from kubex_core.models.status import Status

from .controller import Action

K = TypeVar("K", bound=BaseEntity)


@dataclass(frozen=True)
class Apply(Generic[K]):
    """The object exists and carries the finalizer: bring the world in line."""

    obj: K


@dataclass(frozen=True)
class Cleanup(Generic[K]):
    """The object is being deleted: release what it holds. The finalizer is
    removed once this returns, so it must only return when done; raise (or
    requeue from the error policy) to try again.
    """

    obj: K


FinalizerEvent: TypeAlias = Apply[K] | Cleanup[K]


class FinalizerError(Exception):
    pass


class PatchApi(Protocol):
    """What the finalizer needs of an API; `kubex.api.Api` is one."""

    async def patch(self, name: str, patch: JsonPatch, *, namespace: Any) -> Any: ...


async def finalizer(
    api: PatchApi,
    finalizer_name: str,
    obj: K,
    reconcile: Callable[[FinalizerEvent[K]], Awaitable[Action]],
) -> Action:
    """Runs `reconcile` with `Apply` or `Cleanup`, keeping `finalizer_name` on
    `obj` while it lives.

    - no finalizer, not deleting: adds the finalizer and waits for the change
      that brings, without calling `reconcile`;
    - finalizer, not deleting: `Apply`;
    - finalizer, deleting: `Cleanup`, then removes the finalizer;
    - no finalizer, deleting: nothing left to do.

    Every patch tests the object's uid (when it has one), so it never lands on
    another object recreated under the same name. Adding also tests the
    finalizer list it was computed from; removing tests that the finalizer is
    still at the index it was found at. A concurrent change that would make a
    patch wrong fails it (422) instead of corrupting the list.

    A patch that finds the object gone (a 404 naming it) is not an error: the
    cache had not seen the delete yet. Removing the finalizer then returns
    `reconcile`'s action, the cleanup having run; adding it returns
    `Action.await_change()`, as `Apply` never ran for that object and no
    cleanup is owed. Any other 404, such as a path the server does not serve,
    is raised.
    """
    name = obj.metadata.name
    if not name:
        raise FinalizerError(f"{type(obj).__name__} has no name")
    finalizers = obj.metadata.finalizers or []
    deleting = obj.metadata.deletion_timestamp is not None
    index = finalizers.index(finalizer_name) if finalizer_name in finalizers else None

    if index is not None and not deleting:
        return await reconcile(Apply(obj))
    if index is not None:
        action = await reconcile(Cleanup(obj))
        patch = _patch_of(obj)
        patch.test(f"/metadata/finalizers/{index}", finalizer_name)
        patch.remove(f"/metadata/finalizers/{index}")
        await _patch_unless_gone(api, obj, name, patch)
        return action
    if not deleting:
        patch = _patch_of(obj)
        if finalizers:
            # the API server does not deduplicate finalizers: fail when someone
            # else changed the list meanwhile
            patch.test("/metadata/finalizers", finalizers)
            patch.add("/metadata/finalizers/-", finalizer_name)
        else:
            patch.test("/metadata/finalizers", None)
            patch.add("/metadata/finalizers", [finalizer_name])
        await _patch_unless_gone(api, obj, name, patch)
    # the patch brings a change, which triggers the next reconcile; an object
    # already gone needs none
    return Action.await_change()


async def _patch_unless_gone(
    api: PatchApi, obj: BaseEntity, name: str, patch: JsonPatch
) -> None:
    """Sends `patch`; a 404 naming `obj` means the cache had not seen its delete."""
    try:
        await api.patch(name, patch, namespace=obj.metadata.namespace)
    except NotFound as error:
        if not _says_gone(error, obj):
            raise


def _says_gone(error: NotFound[Any], obj: BaseEntity) -> bool:
    """Whether `error` is about `obj` itself. A path the server does not serve
    is a 404 too, without a name: a misconfigured `api`, which must reach the
    error policy.
    """
    details = error.content.details if isinstance(error.content, Status) else None
    if details is None or details.name != obj.metadata.name:
        return False
    # the resource's plural, which an `api` for another kind does not match
    return details.kind is None or details.kind == type(obj).__RESOURCE_CONFIG__.plural


def _patch_of(obj: BaseEntity) -> JsonPatch:
    """A patch that applies to `obj` only, not to one recreated under its name."""
    patch = JsonPatch()
    if obj.metadata.uid is not None:
        patch.test("/metadata/uid", obj.metadata.uid)
    return patch
