from __future__ import annotations

from typing import Any, Generic, TypeVar, overload

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
from kubex_core.models.interfaces import HasScaleSubresource
from kubex_core.models.resource_config import Scope
from kubex_core.models.scale import Scale
from kubex_core.models.typing import ResourceType

from ._protocol import (
    ApiNamespaceTypes,
    ApiProtocol,
    ApiRequestTimeoutTypes,
    CachedSubresourceDescriptor,
    SubresourceNotAvailable,
    ensure_required_namespace,
)

_S = TypeVar("_S", bound=HasScaleSubresource)

SCALE_SUBRESOURCE = "scale"


class ScaleAccessor(Generic[ResourceType]):
    """Accessor for scale subresource operations."""

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

    async def get(
        self,
        name: str,
        *,
        namespace: ApiNamespaceTypes = Ellipsis,
        request_timeout: ApiRequestTimeoutTypes = Ellipsis,
    ) -> Scale:
        """Read the scale of the specified resource."""
        _namespace = ensure_required_namespace(namespace, self._namespace, self._scope)
        request = self._request_builder.get_subresource(
            SCALE_SUBRESOURCE, name, _namespace, request_timeout=request_timeout
        )
        response = await self._client.request(request)
        return Scale.model_validate_json(response.content)

    async def replace(
        self,
        name: str,
        scale: Scale,
        *,
        namespace: ApiNamespaceTypes = Ellipsis,
        dry_run: DryRunTypes = None,
        field_manager: str | None = None,
        request_timeout: ApiRequestTimeoutTypes = Ellipsis,
    ) -> Scale:
        """Replace the scale of the specified resource."""
        _namespace = ensure_required_namespace(namespace, self._namespace, self._scope)
        options = PostOptions(dry_run=dry_run, field_manager=field_manager)
        request = self._request_builder.replace_subresource(
            SCALE_SUBRESOURCE,
            name,
            _namespace,
            data=scale.model_dump_json(
                by_alias=True, exclude_unset=True, exclude_none=True
            ),
            options=options,
            request_timeout=request_timeout,
        )
        response = await self._client.request(request)
        return Scale.model_validate_json(response.content)

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
    ) -> Scale:
        """Patch the scale of the specified resource."""
        _namespace = ensure_required_namespace(namespace, self._namespace, self._scope)
        options = PatchOptions(
            dry_run=dry_run,
            field_manager=field_manager,
            force=force,
            field_validation=field_validation,
        )
        request = self._request_builder.patch_subresource(
            SCALE_SUBRESOURCE,
            name,
            _namespace,
            options=options,
            patch=patch,
            request_timeout=request_timeout,
        )
        response = await self._client.request(request)
        return Scale.model_validate_json(response.content)


class _ScaleDescriptor(CachedSubresourceDescriptor):
    _marker = HasScaleSubresource
    _accessor_cls = ScaleAccessor
    _error_message = (
        "Scale is only supported for resources with HasScaleSubresource marker"
    )

    @overload
    def __get__(self, instance: None, owner: type) -> _ScaleDescriptor: ...

    @overload
    def __get__(self, instance: ApiProtocol[_S], owner: type) -> ScaleAccessor[_S]: ...

    @overload
    def __get__(
        self, instance: ApiProtocol[Any], owner: type
    ) -> SubresourceNotAvailable: ...

    def __get__(self, instance: Any, owner: type | None = None) -> Any:
        return self._resolve(instance)
