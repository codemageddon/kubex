from __future__ import annotations

from typing import Any, ClassVar, TypeVar, overload

from kubex_core.models.interfaces import HasStatusSubresource
from kubex_core.models.typing import ResourceType

from ._protocol import (
    ApiProtocol,
    CachedSubresourceDescriptor,
    SubresourceNotAvailable,
)
from ._subresource_accessor import ResourceSubresourceAccessor

_St = TypeVar("_St", bound=HasStatusSubresource)

STATUS_SUBRESOURCE = "status"


class StatusAccessor(ResourceSubresourceAccessor[ResourceType]):
    """Accessor for status subresource operations."""

    _subresource: ClassVar[str] = STATUS_SUBRESOURCE


class _StatusDescriptor(CachedSubresourceDescriptor):
    _marker = HasStatusSubresource
    _accessor_cls = StatusAccessor
    _error_message = (
        "Status is only supported for resources with HasStatusSubresource marker"
    )

    @overload
    def __get__(self, instance: None, owner: type) -> _StatusDescriptor: ...

    @overload
    def __get__(
        self, instance: ApiProtocol[_St], owner: type
    ) -> StatusAccessor[_St]: ...

    @overload
    def __get__(
        self, instance: ApiProtocol[Any], owner: type
    ) -> SubresourceNotAvailable: ...

    def __get__(self, instance: Any, owner: type | None = None) -> Any:
        return self._resolve(instance)
