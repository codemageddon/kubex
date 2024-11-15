from __future__ import annotations

import json
from typing import (
    AsyncGenerator,
    Generic,
    Type,
)

from pydantic import ValidationError

from kubex.client.client import Client
from kubex.core.params import (
    DeleteOptions,
    GetOptions,
    ListOptions,
    PatchOptions,
    PostOptions,
    VersionMatch,
    WatchOptions,
)
from kubex.core.patch import (
    ApplyPatch,
    JsonPatch,
    MergePatch,
    StrategicMergePatch,
)
from kubex.core.request_builder.builder import RequestBuilder
from kubex.models.list_entity import ListEntity
from kubex.models.resource_config import Scope
from kubex.models.status import Status
from kubex.models.typing import (
    ResourceType,
)
from kubex.models.watch_event import WatchEvent

from ._logs import LogsMixin
from ._metadata import MetadataMixin


class Api(Generic[ResourceType], MetadataMixin[ResourceType], LogsMixin[ResourceType]):
    def __init__(
        self,
        resource_type: Type[ResourceType],
        client: Client,
        *,
        namespace: str | None = None,
    ) -> None:
        self._resource = resource_type
        self._client = client
        self._request_builder = RequestBuilder(
            resource_config=resource_type.__RESOURCE_CONFIG__,
        )
        self._request_builder.namespace = namespace
        self._namespace: str | None = namespace

    @classmethod
    async def create_api(
        cls,
        resource_type: Type[ResourceType],
        *,
        client: Client | None = None,
        namespace: str | None = None,
    ) -> Api[ResourceType]:
        client = client or await Client.create()
        return cls(resource_type, client=client, namespace=namespace)

    def _check_namespace(self) -> None:
        if (
            self._namespace is None
            and self._resource.__RESOURCE_CONFIG__.scope == Scope.NAMESPACE
        ):
            raise ValueError("Namespace is required")

    async def get(self, name: str, resource_version: str | None = None) -> ResourceType:
        options = GetOptions(resource_version=resource_version)
        return await self.get_with_options(name, options)

    async def get_with_options(self, name: str, options: GetOptions) -> ResourceType:
        self._check_namespace()
        request = self._request_builder.get(name, options)
        response = await self._client.request(request)
        return self._resource.model_validate_json(response.content)

    async def list(
        self,
        label_selector: str | None = None,
        field_selector: str | None = None,
        timeout: int | None = None,
        limit: int | None = None,
        continue_token: str | None = None,
        version_match: VersionMatch | None = None,
        resource_version: str | None = None,
    ) -> ListEntity[ResourceType]:
        options = ListOptions(
            label_selector=label_selector,
            field_selector=field_selector,
            timeout=timeout,
            limit=limit,
            continue_token=continue_token,
            version_match=version_match,
            resource_version=resource_version,
        )
        return await self.list_with_options(options)

    async def list_with_options(self, options: ListOptions) -> ListEntity[ResourceType]:
        request = self._request_builder.list(options)
        response = await self._client.request(request)
        # json_ = response.json()
        list_model = self._resource.__RESOURCE_CONFIG__.list_model
        return list_model.model_validate_json(response.content)

    async def create(self, data: ResourceType) -> ResourceType:
        options = PostOptions()
        return await self.create_with_options(data, options)

    async def create_with_options(
        self, data: ResourceType, options: PostOptions
    ) -> ResourceType:
        self._check_namespace()
        request = self._request_builder.create(
            options,
            data.model_dump_json(by_alias=True, exclude_unset=True, exclude_none=True),
        )
        response = await self._client.request(request)
        return self._resource.model_validate_json(response.content)

    async def delete(
        self, name: str, options: DeleteOptions | None = None
    ) -> Status | ResourceType:
        self._check_namespace()
        if options is None:
            options = DeleteOptions.default()
        request = self._request_builder.delete(name, options)
        response = await self._client.request(request)
        try:
            return Status.model_validate_json(response.content)
        except ValidationError:
            return self._resource.model_validate_json(response.content)

    async def delete_collection(
        self, list_options: ListOptions, delete_options: DeleteOptions
    ) -> Status | ListEntity[ResourceType]:
        request = self._request_builder.delete_collection(list_options, delete_options)
        response = await self._client.request(request)
        list_model = self._resource.__RESOURCE_CONFIG__.list_model
        try:
            return Status.model_validate_json(response.content)
        except ValidationError:
            return list_model.model_validate_json(response.content)

    async def patch(
        self,
        name: str,
        patch: ApplyPatch[ResourceType]
        | MergePatch[ResourceType]
        | StrategicMergePatch[ResourceType]
        | JsonPatch,
        options: PatchOptions,
    ) -> ResourceType:
        self._check_namespace()
        request = self._request_builder.patch(name, options, patch)
        response = await self._client.request(request)
        return self._resource.model_validate_json(response.content)

    async def replace(
        self, name: str, data: ResourceType, options: PostOptions
    ) -> ResourceType:
        self._check_namespace()
        request = self._request_builder.replace(
            name,
            options,
            data.model_dump_json(by_alias=True, exclude_unset=True, exclude_none=True),
        )
        response = await self._client.request(request)
        return self._resource.model_validate_json(response.content)

    async def watch(
        self, options: WatchOptions | None = None, resource_version: str | None = None
    ) -> AsyncGenerator[WatchEvent[ResourceType], None]:
        if options is None:
            options = WatchOptions.default()
        request = self._request_builder.watch(
            options, resource_version=resource_version
        )
        async for line in self._client.stream_lines(request):
            yield WatchEvent(self._resource, json.loads(line))
