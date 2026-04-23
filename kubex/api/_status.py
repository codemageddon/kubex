from __future__ import annotations

from typing import Any, Generic, TypeVar, overload

from kubex.client.client import BaseClient
from kubex.core.params import NamespaceTypes
from kubex.core.request_builder.builder import RequestBuilder
from kubex_core.models.interfaces import HasStatusSubresource
from kubex_core.models.resource_config import Scope
from kubex_core.models.typing import ResourceType

from ._protocol import ApiProtocol, CachedSubresourceDescriptor, SubresourceNotAvailable

_St = TypeVar("_St", bound=HasStatusSubresource)


class StatusAccessor(Generic[ResourceType]):
    """Accessor for status subresource operations."""

    def __init__(
        self,
        client: BaseClient,
        request_builder: RequestBuilder,
        namespace: NamespaceTypes,
        scope: Scope,
    ) -> None:
        self._client = client
        self._request_builder = request_builder
        self._namespace = namespace
        self._scope = scope


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
