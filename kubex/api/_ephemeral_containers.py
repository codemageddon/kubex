from __future__ import annotations

from typing import Any, ClassVar, TypeVar, overload

from kubex_core.models.interfaces import HasEphemeralContainers
from kubex_core.models.typing import ResourceType

from ._protocol import (
    ApiProtocol,
    CachedSubresourceDescriptor,
    SubresourceNotAvailable,
)
from ._subresource_accessor import ResourceSubresourceAccessor

_EC = TypeVar("_EC", bound=HasEphemeralContainers)

EPHEMERAL_CONTAINERS_SUBRESOURCE = "ephemeralcontainers"


class EphemeralContainersAccessor(ResourceSubresourceAccessor[ResourceType]):
    """Accessor for ephemeral containers subresource operations."""

    _subresource: ClassVar[str] = EPHEMERAL_CONTAINERS_SUBRESOURCE


class _EphemeralContainersDescriptor(CachedSubresourceDescriptor):
    _marker = HasEphemeralContainers
    _accessor_cls = EphemeralContainersAccessor
    _error_message = "Ephemeral containers is only supported for resources with HasEphemeralContainers marker"

    @overload
    def __get__(
        self, instance: None, owner: type
    ) -> _EphemeralContainersDescriptor: ...

    @overload
    def __get__(
        self, instance: ApiProtocol[_EC], owner: type
    ) -> EphemeralContainersAccessor[_EC]: ...

    @overload
    def __get__(
        self, instance: ApiProtocol[Any], owner: type
    ) -> SubresourceNotAvailable: ...

    def __get__(self, instance: Any, owner: type | None = None) -> Any:
        return self._resolve(instance)
