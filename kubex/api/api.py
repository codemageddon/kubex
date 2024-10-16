from __future__ import annotations

import json
from typing import (
    AsyncGenerator,
    Generic,
    Self,
    Type,
)

from yaml import safe_dump

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
    PatchTypes,
    StrategicMergePatch,
)
from kubex.core.request_builder.builder import RequestBuilder
from kubex.models.base import (
    ListEntity,
    ResourceType,
    Scope,
)
from kubex.models.watch_event import WatchEvent

from .logs import LogsMixin


class Api(Generic[ResourceType], LogsMixin[ResourceType]):
    def __init__(
        self,
        resource_type: Type[ResourceType],
        *,
        client: Client | None = None,
        namespace: str | None = None,
    ) -> None:
        self._resource = resource_type
        self._client = client or Client()
        self._request_builder = RequestBuilder(
            resource_config=resource_type.__RESOURCE_CONFIG__,
        )
        self._request_builder.namespace = namespace
        self._namespace: str | None = namespace

    def with_namespace(self, namespace: str) -> Self:
        self._namespace = namespace
        self._request_builder.namespace = namespace
        return self

    def with_default_namespace(self) -> Self:
        self._namespace = self._client.configuration.namespace
        self._request_builder.namespace = self._namespace
        return self

    def without_namespace(self) -> Self:
        self._namespace = None
        self._request_builder.namespace = None
        return self

    @classmethod
    def all(
        cls: Type[Self], resource: Type[ResourceType], client: Client | None = None
    ) -> Self:
        api: Self = cls(resource, client=client)
        return api

    @classmethod
    def namespaced(
        cls: Type[Self],
        resource: Type[ResourceType],
        namespace: str,
        client: Client | None = None,
    ) -> Self:
        api: Self = cls(resource, client=client, namespace=namespace)
        return api

    @classmethod
    def default_namespaced(
        cls: Type[Self], resource: Type[ResourceType], client: Client | None = None
    ) -> Self:
        if client is None:
            client = Client()
        return cls.namespaced(
            resource, namespace=client.configuration.namespace, client=client
        )

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
        async with self._client.get_client() as client:
            response = await client.get(request.url, params=request.query_params)
            response.raise_for_status()
            return self._resource.model_validate_json(response.json())

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
        async with self._client.get_client() as client:
            response = await client.get(request.url, params=request.query_params)
            response.raise_for_status()
            json_ = response.json()
            list_model = self._resource.__RESOURCE_CONFIG__.list_model
            return list_model.model_validate(json_)

    async def create(self, data: ResourceType) -> ResourceType:
        options = PostOptions()
        return await self.create_with_options(data, options)

    async def create_with_options(
        self, data: ResourceType, options: PostOptions
    ) -> ResourceType:
        self._check_namespace()
        request = self._request_builder.create(options)
        async with self._client.get_client() as client:
            response = await client.post(
                request.url,
                json=data.model_dump(
                    by_alias=True, exclude_unset=True, exclude_none=True
                ),
            )
            response.raise_for_status()
            return self._resource.model_validate(response.json())

    # TODO: Status is also possible to return
    async def delete(
        self, name: str, options: DeleteOptions | None = None
    ) -> ResourceType:
        self._check_namespace()
        if options is None:
            options = DeleteOptions.default()
        request = self._request_builder.delete(name, options)
        async with self._client.get_client() as client:
            response = await client.request(
                method="DELETE", url=request.url, json=request.body
            )
            response.raise_for_status()
            return self._resource.model_validate(response.json())

    # TODO: Status is also possible to return
    async def delete_collection(
        self, list_options: ListOptions, delete_options: DeleteOptions
    ) -> ListEntity[ResourceType]:
        request = self._request_builder.delete_collection(list_options, delete_options)
        async with self._client.get_client() as client:
            list_model = self._resource.__RESOURCE_CONFIG__.list_model
            response = await client.request(
                method="DELETE", url=request.url, json=request.body
            )
            response.raise_for_status()
            return list_model.model_validate(response.json())

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

        request = self._request_builder.patch(name, patch_type, options)
        async with self._client.get_client() as client:
            response = await client.patch(
                url=request.url, content=body, headers=request.headers
            )
            response.raise_for_status()
            return self._resource.model_validate(response.json())

    async def replace(
        self, name: str, data: ResourceType, options: PostOptions
    ) -> ResourceType:
        self._check_namespace()
        request = self._request_builder.replace(name, options)
        async with self._client.get_client() as client:
            response = await client.put(
                request.url,
                content=data.model_dump_json(
                    by_alias=True, exclude_unset=True, exclude_none=True
                ),
            )
            response.raise_for_status()
            return self._resource.model_validate(response.json())

    async def watch(
        self, options: WatchOptions | None = None, resource_version: str | None = None
    ) -> AsyncGenerator[WatchEvent[ResourceType], None]:
        if options is None:
            options = WatchOptions.default()
        request = self._request_builder.watch(
            options, resource_version=resource_version
        )
        async with self._client.get_client() as client:
            async with client.stream(
                "GET", request.url, params=request.query_params, headers=request.headers
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    yield WatchEvent(self._resource, json.loads(line))
