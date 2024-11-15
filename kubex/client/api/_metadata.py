from __future__ import annotations

import json
from typing import AsyncGenerator

from kubex.client.api._protocol import ApiProtocol
from kubex.core.params import GetOptions, ListOptions, PatchOptions, WatchOptions
from kubex.core.patch import (
    ApplyPatch,
    JsonPatch,
    MergePatch,
    StrategicMergePatch,
)
from kubex.models.list_entity import ListEntity
from kubex.models.partial_object_meta import PartialObjectMetadata
from kubex.models.typing import (
    ResourceType,
)
from kubex.models.watch_event import WatchEvent


class MetadataMixin(ApiProtocol[ResourceType]):
    async def get_metadata(
        self, name: str, options: GetOptions | None = None
    ) -> PartialObjectMetadata:
        self._check_namespace()
        request = self._request_builder.get_metadata(
            name, options=options or GetOptions.default()
        )
        response = await self._client.request(request)
        return PartialObjectMetadata.model_validate_json(response.content)

    async def list_metadata(
        self, options: ListOptions | None = None
    ) -> ListEntity[PartialObjectMetadata]:
        request = self._request_builder.list_metadata(options or ListOptions.default())
        response = await self._client.request(request)
        model = PartialObjectMetadata.__RESOURCE_CONFIG__.list_model
        return model.model_validate_json(response.content)

    async def patch_metadata(
        self,
        name: str,
        patch: ApplyPatch[ResourceType]
        | MergePatch[ResourceType]
        | StrategicMergePatch[ResourceType]
        | JsonPatch,
        options: PatchOptions,
    ) -> PartialObjectMetadata:
        self._check_namespace()
        request = self._request_builder.patch_metadata(name, options, patch)
        response = await self._client.request(request)
        return PartialObjectMetadata.model_validate_json(response.content)

    async def watch_metadata(
        self, options: WatchOptions | None = None, resource_version: str | None = None
    ) -> AsyncGenerator[
        WatchEvent[PartialObjectMetadata],
        None,
    ]:
        request = self._request_builder.watch_metadata(
            options or WatchOptions.default(), resource_version=resource_version
        )
        async for line in self._client.stream_lines(request):
            yield WatchEvent(PartialObjectMetadata, json.loads(line))
