from __future__ import annotations

from typing import Any, Generic, Type, TypeVar, overload

from kubex.client.client import BaseClient
from kubex.core.params import DryRunTypes, NamespaceTypes, PostOptions
from kubex.core.request_builder.builder import RequestBuilder
from kubex_core.models.eviction import Eviction
from kubex_core.models.interfaces import Evictable
from kubex_core.models.resource_config import Scope
from kubex_core.models.status import Status
from kubex_core.models.typing import ResourceType

from ._protocol import (
    ApiNamespaceTypes,
    ApiProtocol,
    ApiRequestTimeoutTypes,
    CachedSubresourceDescriptor,
    SubresourceNotAvailable,
    ensure_required_namespace,
)

_E = TypeVar("_E", bound=Evictable)

EVICTION_SUBRESOURCE = "eviction"


class EvictionAccessor(Generic[ResourceType]):
    """Accessor for eviction subresource operations."""

    def __init__(
        self,
        client: BaseClient,
        request_builder: RequestBuilder,
        namespace: NamespaceTypes,
        scope: Scope,
        resource_type: Type[ResourceType],
    ) -> None:
        self._client = client
        self._request_builder = request_builder
        self._namespace = namespace
        self._scope = scope
        self._resource_type = resource_type

    async def create(
        self,
        name: str,
        eviction: Eviction,
        *,
        namespace: ApiNamespaceTypes = Ellipsis,
        dry_run: DryRunTypes = None,
        field_manager: str | None = None,
        request_timeout: ApiRequestTimeoutTypes = Ellipsis,
    ) -> Status:
        """Create an eviction for the specified resource."""
        _namespace = ensure_required_namespace(namespace, self._namespace, self._scope)
        options = PostOptions(dry_run=dry_run, field_manager=field_manager)
        request = self._request_builder.create_subresource(
            EVICTION_SUBRESOURCE,
            name,
            _namespace,
            data=eviction.model_dump_json(
                by_alias=True, exclude_unset=True, exclude_none=True
            ),
            options=options,
            request_timeout=request_timeout,
        )
        response = await self._client.request(request)
        return Status.model_validate_json(response.content)


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
