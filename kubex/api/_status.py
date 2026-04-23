from __future__ import annotations

from typing import Any, Generic, Type, TypeVar, overload

from kubex.client.client import BaseClient
from kubex.core.params import (
    DryRunTypes,
    FieldValidation,
    NamespaceTypes,
    PatchOptions,
    PostOptions,
)
from kubex.core.patch import Patch
from kubex.core.request_builder.builder import RequestBuilder
from kubex_core.models.interfaces import HasStatusSubresource
from kubex_core.models.resource_config import Scope
from kubex_core.models.typing import ResourceType

from ._protocol import (
    ApiNamespaceTypes,
    ApiProtocol,
    ApiRequestTimeoutTypes,
    CachedSubresourceDescriptor,
    SubresourceNotAvailable,
    ensure_required_namespace,
)

_St = TypeVar("_St", bound=HasStatusSubresource)

STATUS_SUBRESOURCE = "status"


class StatusAccessor(Generic[ResourceType]):
    """Accessor for status subresource operations."""

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

    async def get(
        self,
        name: str,
        *,
        namespace: ApiNamespaceTypes = Ellipsis,
        request_timeout: ApiRequestTimeoutTypes = Ellipsis,
    ) -> ResourceType:
        """Read the status of the specified resource."""
        _namespace = ensure_required_namespace(namespace, self._namespace, self._scope)
        request = self._request_builder.get_subresource(
            STATUS_SUBRESOURCE, name, _namespace, request_timeout=request_timeout
        )
        response = await self._client.request(request)
        return self._resource_type.model_validate_json(response.content)

    async def replace(
        self,
        name: str,
        data: ResourceType,
        *,
        namespace: ApiNamespaceTypes = Ellipsis,
        dry_run: DryRunTypes = None,
        field_manager: str | None = None,
        request_timeout: ApiRequestTimeoutTypes = Ellipsis,
    ) -> ResourceType:
        """Replace the status of the specified resource."""
        _namespace = ensure_required_namespace(namespace, self._namespace, self._scope)
        options = PostOptions(dry_run=dry_run, field_manager=field_manager)
        request = self._request_builder.replace_subresource(
            STATUS_SUBRESOURCE,
            name,
            _namespace,
            data=data.model_dump_json(
                by_alias=True, exclude_unset=True, exclude_none=True
            ),
            options=options,
            request_timeout=request_timeout,
        )
        response = await self._client.request(request)
        return self._resource_type.model_validate_json(response.content)

    async def patch(
        self,
        name: str,
        patch: Patch,
        *,
        namespace: ApiNamespaceTypes = Ellipsis,
        dry_run: DryRunTypes = None,
        field_manager: str | None = None,
        force: bool | None = None,
        field_validation: FieldValidation | None = None,
        request_timeout: ApiRequestTimeoutTypes = Ellipsis,
    ) -> ResourceType:
        """Patch the status of the specified resource."""
        _namespace = ensure_required_namespace(namespace, self._namespace, self._scope)
        options = PatchOptions(
            dry_run=dry_run,
            field_manager=field_manager,
            force=force,
            field_validation=field_validation,
        )
        request = self._request_builder.patch_subresource(
            STATUS_SUBRESOURCE,
            name,
            _namespace,
            options=options,
            patch=patch,
            request_timeout=request_timeout,
        )
        response = await self._client.request(request)
        return self._resource_type.model_validate_json(response.content)


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
