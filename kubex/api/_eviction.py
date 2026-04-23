from __future__ import annotations

from typing import Any, Generic, TypeVar, overload

from kubex.client.client import BaseClient
from kubex.core.params import NamespaceTypes
from kubex.core.request_builder.builder import RequestBuilder
from kubex_core.models.interfaces import Evictable
from kubex_core.models.resource_config import Scope
from kubex_core.models.typing import ResourceType

from ._protocol import ApiProtocol, CachedSubresourceDescriptor, SubresourceNotAvailable

_E = TypeVar("_E", bound=Evictable)


class EvictionAccessor(Generic[ResourceType]):
    """Accessor for eviction subresource operations."""

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


class _EvictionDescriptor(CachedSubresourceDescriptor):
    _marker = Evictable
    _accessor_cls = EvictionAccessor
    _error_message = "Eviction is only supported for resources with Evictable marker"

    @overload
    def __get__(self, instance: None, owner: type) -> _EvictionDescriptor: ...

    @overload
    def __get__(
        self, instance: ApiProtocol[_E], owner: type
    ) -> EvictionAccessor[_E]: ...

    @overload
    def __get__(
        self, instance: ApiProtocol[Any], owner: type
    ) -> SubresourceNotAvailable: ...

    def __get__(self, instance: Any, owner: type | None = None) -> Any:
        return self._resolve(instance)
