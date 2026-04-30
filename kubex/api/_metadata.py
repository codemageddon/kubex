from __future__ import annotations

import json
from typing import AsyncGenerator, Generic, Type

from kubex.client.client import BaseClient
from kubex.core.params import (
    DryRunTypes,
    FieldValidation,
    GetOptions,
    ListOptions,
    NamespaceTypes,
    PatchOptions,
    ResourceVersionTypes,
    VersionMatch,
    WatchOptions,
)
from kubex.core.patch import Patch
from kubex.core.request_builder.builder import RequestBuilder
from kubex_core.models.list_entity import ListEntity
from kubex_core.models.partial_object_meta import PartialObjectMetadata
from kubex_core.models.resource_config import Scope
from kubex_core.models.typing import ResourceType
from kubex_core.models.watch_event import WatchEvent

from ._protocol import (
    ApiNamespaceTypes,
    ApiRequestTimeoutTypes,
    ensure_optional_namespace,
    ensure_required_namespace,
)


class MetadataAccessor(Generic[ResourceType]):
    """Accessor for metadata subresource operations."""

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
        resource_version: ResourceVersionTypes = None,
        request_timeout: ApiRequestTimeoutTypes = Ellipsis,
    ) -> PartialObjectMetadata:
        """Read metadata of the specified resource."""
        _namespace = ensure_required_namespace(namespace, self._namespace, self._scope)
        options = GetOptions(resource_version=resource_version)
        request = self._request_builder.get_metadata(
            name, _namespace, options=options, request_timeout=request_timeout
        )
        response = await self._client.request(request)
        return PartialObjectMetadata.model_validate_json(response.content)

    async def list(
        self,
        *,
        namespace: ApiNamespaceTypes = Ellipsis,
        label_selector: str | None = None,
        field_selector: str | None = None,
        timeout_seconds: int | None = None,
        limit: int | None = None,
        continue_token: str | None = None,
        version_match: VersionMatch | None = None,
        resource_version: ResourceVersionTypes = None,
        request_timeout: ApiRequestTimeoutTypes = Ellipsis,
    ) -> ListEntity[PartialObjectMetadata]:
        """List metadata of resources."""
        _namespace = ensure_optional_namespace(namespace, self._namespace, self._scope)
        options = ListOptions(
            label_selector=label_selector,
            field_selector=field_selector,
            timeout_seconds=timeout_seconds,
            limit=limit,
            continue_token=continue_token,
            version_match=version_match,
            resource_version=resource_version,
        )
        request = self._request_builder.list_metadata(
            _namespace, options, request_timeout=request_timeout
        )
        response = await self._client.request(request)
        model = PartialObjectMetadata.__RESOURCE_CONFIG__.list_model
        return model.model_validate_json(response.content)

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
    ) -> PartialObjectMetadata:
        """Patch metadata of the specified resource."""
        _namespace = ensure_required_namespace(namespace, self._namespace, self._scope)
        options = PatchOptions(
            dry_run=dry_run,
            field_manager=field_manager,
            force=force,
            field_validation=field_validation,
        )
        request = self._request_builder.patch_metadata(
            name, _namespace, options, patch, request_timeout=request_timeout
        )
        response = await self._client.request(request)
        return PartialObjectMetadata.model_validate_json(response.content)

    async def watch(
        self,
        *,
        namespace: ApiNamespaceTypes = Ellipsis,
        label_selector: str | None = None,
        field_selector: str | None = None,
        allow_bookmarks: bool | None = None,
        send_initial_events: bool | None = None,
        timeout_seconds: int | None = None,
        resource_version: ResourceVersionTypes = None,
        request_timeout: ApiRequestTimeoutTypes = Ellipsis,
    ) -> AsyncGenerator[
        WatchEvent[PartialObjectMetadata],
        None,
    ]:
        """Watch for metadata changes of resources."""
        _namespace = ensure_optional_namespace(namespace, self._namespace, self._scope)
        options = WatchOptions(
            label_selector=label_selector,
            field_selector=field_selector,
            allow_bookmarks=allow_bookmarks,
            send_initial_events=send_initial_events,
            timeout_seconds=timeout_seconds,
        )
        request = self._request_builder.watch_metadata(
            _namespace,
            options,
            resource_version=resource_version,
            request_timeout=request_timeout,
        )
        async for line in self._client.stream_lines(request):
            yield WatchEvent(PartialObjectMetadata, json.loads(line))
