from __future__ import annotations

from typing import Any, ClassVar, TypeVar, overload

from kubex_core.models.interfaces import HasResize
from kubex_core.models.typing import ResourceType

from ._protocol import (
    ApiProtocol,
    CachedSubresourceDescriptor,
    SubresourceNotAvailable,
)
from ._subresource_accessor import ResourceSubresourceAccessor

_R = TypeVar("_R", bound=HasResize)

RESIZE_SUBRESOURCE = "resize"


class ResizeAccessor(ResourceSubresourceAccessor[ResourceType]):
    """Accessor for resize subresource operations."""

    _subresource: ClassVar[str] = RESIZE_SUBRESOURCE


class _ResizeDescriptor(CachedSubresourceDescriptor):
    _marker = HasResize
    _accessor_cls = ResizeAccessor
    _error_message = "Resize is only supported for resources with HasResize marker"

    @overload
    def __get__(self, instance: None, owner: type) -> _ResizeDescriptor: ...

    @overload
    def __get__(self, instance: ApiProtocol[_R], owner: type) -> ResizeAccessor[_R]: ...

    @overload
    def __get__(
        self, instance: ApiProtocol[Any], owner: type
    ) -> SubresourceNotAvailable: ...

    def __get__(self, instance: Any, owner: type | None = None) -> Any:
        return self._resolve(instance)
