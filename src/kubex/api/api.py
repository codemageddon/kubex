from __future__ import annotations

import json
from typing import AsyncGenerator, Generic, Self, Type, cast

from yaml import safe_dump

from kubex.api.params import (
    DeleteOptions,
    GetOptions,
    ListOptions,
    PatchOptions,
    PostOptions,
    VersionMatch,
    WatchOptions,
)
from kubex.api.patch import (
    ApplyPatch,
    JsonPatch,
    MergePatch,
    PatchTypes,
    StrategicMergePatch,
)
from kubex.api.request import RequestBuilder
from kubex.api.tmp_client import get_client
from kubex.models.base import ListEntity, ResourceType
from kubex.models.watch_event import WatchEvent


class ClientConfiguration:
    def __init__(self) -> None:
        self.namespace = "default"


class Client:
    def __init__(self) -> None:
        self.configuration = ClientConfiguration()


class Api(Generic[ResourceType]):
    request_builder: RequestBuilder
    client: Client
    namespace: str | None
    resource: Type[ResourceType]

    @classmethod
    def all(cls: Type[Self], client: Client, resource: Type[ResourceType]) -> Self:
        api: Self = cls()
        api.request_builder = RequestBuilder(url=resource.__RESOURCE_CONFIG__.url())
        api.client = client
        api.namespace = None
        api.resource = resource
        return api

    @classmethod
    def namespaced(
        cls: Type[Self], client: Client, resource: Type[ResourceType], namespace: str
    ) -> Self:
        api: Self = cls()
        api.request_builder = RequestBuilder(
            url=resource.__RESOURCE_CONFIG__.url(namespace=namespace)
        )
        api.client = client
        api.namespace = namespace
        api.resource = resource
        return api

    @classmethod
    def default_namespaced(
        cls: Type[Self], client: Client, resource: Type[ResourceType]
    ) -> Self:
        return cls.namespaced(
            client, resource, namespace=client.configuration.namespace
        )

    async def get(self, name: str, resource_version: str | None = None) -> ResourceType:
        options = GetOptions(resource_version=resource_version)
        return await self.get_with_options(name, options)

    async def get_with_options(self, name: str, options: GetOptions) -> ResourceType:
        request = self.request_builder.get(name, options)
        async with get_client() as client:
            response = await client.get(request.url, params=request.query_params)
            response.raise_for_status()
            return cast(
                ResourceType, self.resource.model_validate_json(response.json())
            )

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
        request = self.request_builder.list(options)
        async with get_client() as client:
            response = await client.get(request.url, params=request.query_params)
            response.raise_for_status()
            return cast(
                ListEntity[ResourceType],
                self.resource.model_validate(response.json()),
            )

    async def create(self, data: ResourceType) -> ResourceType:
        options = PostOptions()
        return await self.create_with_options(data, options)

    async def create_with_options(
        self, data: ResourceType, options: PostOptions
    ) -> ResourceType:
        request = self.request_builder.create(options)
        async with get_client() as client:
            response = await client.post(request.url, json=data.dict())
            response.raise_for_status()
            return cast(ResourceType, self.resource.model_validate(response.json()))

    # TODO: Status is also possible to return
    async def delete(
        self, name: str, options: DeleteOptions | None = None
    ) -> ResourceType:
        if options is None:
            options = DeleteOptions.default()
        request = self.request_builder.delete(name, options)
        async with get_client() as client:
            response = await client.request(
                method="DELETE", url=request.url, json=request.body
            )
            response.raise_for_status()
            return cast(ResourceType, self.resource.model_validate(response.json()))

    # TODO: Status is also possible to return
    async def delete_collection(
        self, list_options: ListOptions, delete_options: DeleteOptions
    ) -> ListEntity[ResourceType]:
        request = self.request_builder.delete_collection(list_options, delete_options)
        async with get_client() as client:
            response = await client.request(
                method="DELETE", url=request.url, json=request.body
            )
            response.raise_for_status()
            return response.json()

    async def patch(
        self,
        name: str,
        patch: ApplyPatch[ResourceType]
        | MergePatch[ResourceType]
        | StrategicMergePatch[ResourceType]
        | JsonPatch,
        options: PatchOptions,
    ) -> ResourceType:
        match patch:
            case ApplyPatch():
                patch_type = PatchTypes.APPLY_PATCH
                body = safe_dump(
                    patch.body.model_dump(
                        by_alias=True, exclude_unset=True, exclude_none=True
                    )
                )
            case MergePatch():
                patch_type = PatchTypes.MERGE_PATCH
                body = patch.body.model_dump_json(
                    by_alias=True, exclude_unset=True, exclude_none=True
                )
            case StrategicMergePatch():
                patch_type = PatchTypes.STRATEGIC_MERGE_PATCH
                body = patch.body.model_dump_json(
                    by_alias=True, exclude_unset=True, exclude_none=True
                )
            case JsonPatch():
                patch_type = PatchTypes.JSON_PATCH
                body = json.dumps(patch.body)
            case _:
                raise ValueError(f"Unsupported patch type: {patch}")

        request = self.request_builder.patch(name, patch_type, options)
        async with get_client() as client:
            response = await client.patch(
                url=request.url, content=body, headers=request.headers
            )
            response.raise_for_status()
            return cast(ResourceType, self.resource.model_validate(response.json()))

    async def replace(
        self, name: str, data: ResourceType, options: PostOptions
    ) -> ResourceType:
        request = self.request_builder.replace(name, options)
        async with get_client() as client:
            response = await client.put(
                request.url,
                content=data.model_dump_json(
                    by_alias=True, exclude_unset=True, exclude_none=True
                ),
            )
            response.raise_for_status()
            return cast(ResourceType, self.resource.model_validate(response.json()))

    async def watch(
        self, options: WatchOptions, resource_version: str | None = None
    ) -> AsyncGenerator[WatchEvent[ResourceType], None]:
        query_params = options.as_query_params()
        request = self.request_builder.watch(options, resource_version=resource_version)
        async with get_client() as client:
            async with client.stream(
                "GET", request.url, params=query_params
            ) as response:
                response.raise_for_status()
                async for chunk in response.aiter_lines():
                    yield WatchEvent(self.resource, json.loads(chunk))
