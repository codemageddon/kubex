from __future__ import annotations

import json
from typing import AsyncGenerator

from kubex.client.api._protocol import ApiNamespaceTypes, ApiProtocol
from kubex.core.params import (
    DryRunTypes,
    FieldValidation,
    GetOptions,
    ListOptions,
    PatchOptions,
    ResourceVersionTypes,
    VersionMatch,
    WatchOptions,
)
from kubex.core.patch import Patch
from kubex.models.list_entity import ListEntity
from kubex.models.partial_object_meta import PartialObjectMetadata
from kubex.models.typing import (
    ResourceType,
)
from kubex.models.watch_event import WatchEvent


class MetadataMixin(ApiProtocol[ResourceType]):
    async def get_metadata(
        self,
        name: str,
        *,
        namespace: ApiNamespaceTypes = Ellipsis,
        resource_version: ResourceVersionTypes = None,
    ) -> PartialObjectMetadata:
        _namespace = self._ensure_required_namespace(namespace)
        options = GetOptions(resource_version=resource_version)
        request = self._request_builder.get_metadata(name, _namespace, options=options)
        response = await self._client.request(request)
        return PartialObjectMetadata.model_validate_json(response.content)

    async def list_metadata(
        self,
        *,
        namespace: ApiNamespaceTypes = Ellipsis,
        label_selector: str | None = None,
        field_selector: str | None = None,
        timeout: int | None = None,
        limit: int | None = None,
        continue_token: str | None = None,
        version_match: VersionMatch | None = None,
        resource_version: ResourceVersionTypes = None,
    ) -> ListEntity[PartialObjectMetadata]:
        _namespace = self._ensure_optional_namespace(namespace)
        options = ListOptions(
            label_selector=label_selector,
            field_selector=field_selector,
            timeout=timeout,
            limit=limit,
            continue_token=continue_token,
            version_match=version_match,
            resource_version=resource_version,
        )
        request = self._request_builder.list_metadata(_namespace, options)
        response = await self._client.request(request)
        model = PartialObjectMetadata.__RESOURCE_CONFIG__.list_model
        return model.model_validate_json(response.content)

    async def patch_metadata(
        self,
        name: str,
        patch: Patch,
        *,
        namespace: ApiNamespaceTypes = Ellipsis,
        dry_run: DryRunTypes = None,
        field_manager: str | None = None,
        force: bool | None = None,
        field_validation: FieldValidation | None = None,
    ) -> PartialObjectMetadata:
        _namespace = self._ensure_required_namespace(namespace)
        options = PatchOptions(
            dry_run=dry_run,
            field_manager=field_manager,
            force=force,
            field_validation=field_validation,
        )
        request = self._request_builder.patch_metadata(name, _namespace, options, patch)
        response = await self._client.request(request)
        return PartialObjectMetadata.model_validate_json(response.content)

    async def watch_metadata(
        self,
        *,
        namespace: ApiNamespaceTypes = Ellipsis,
        label_selector: str | None = None,
        field_selector: str | None = None,
        allow_bookmarks: bool | None = None,
        send_initial_events: bool | None = None,
        timeout_seconds: int | None = None,
        resource_version: ResourceVersionTypes = None,
    ) -> AsyncGenerator[
        WatchEvent[PartialObjectMetadata],
        None,
    ]:
        _namespace = self._ensure_optional_namespace(namespace)
        options = WatchOptions(
            label_selector=label_selector,
            field_selector=field_selector,
            allow_bookmarks=allow_bookmarks,
            send_initial_events=send_initial_events,
            timeout_seconds=timeout_seconds,
        )
        request = self._request_builder.watch_metadata(
            _namespace, options, resource_version=resource_version
        )
        async for line in self._client.stream_lines(request):
            yield WatchEvent(PartialObjectMetadata, json.loads(line))
