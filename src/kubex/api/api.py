from __future__ import annotations

import json
from enum import Enum
from typing import Any, AsyncGenerator, ClassVar, Generic, Self, Type, cast

import httpx
from yaml import safe_dump

from kubex.models.base import ListEntity, ResourceType
from kubex.models.watch_event import WatchEvent

_BASE_URL = "https://127.0.0.1:6443"
_CERT = (
    "/Users/codemageddon/github.com/codemageddon/kubex/scratches/.certs/client_cert.crt",
    "/Users/codemageddon/github.com/codemageddon/kubex/scratches/.certs/client_key.pem",
)
_VERIFY = "/Users/codemageddon/github.com/codemageddon/kubex/scratches/.certs/server.ca"

CLIENT_PARAMS = {
    "base_url": _BASE_URL,
    "cert": _CERT,
    "verify": _VERIFY,
}


class VersionMatch(str, Enum):
    EXACT = "Exact"
    NOT_EXACT = "NotOlderThan"


class PropagationPolicy(str, Enum):
    BACKGROUND = "Background"
    FOREGROUND = "Foreground"
    ORPHAN = "Orphan"


class FieldValidation(str, Enum):
    IGNORE = "Ignore"
    STRICT = "Strict"
    WARN = "Warn"


class Precondition:
    def __init__(
        self,
        resource_version: str | None = None,
        uid: str | None = None,
    ) -> None:
        self.resource_version = resource_version
        self.uid = uid


class ListOptions:
    def __init__(
        self,
        label_selector: str | None = None,
        field_selector: str | None = None,
        timeout: int | None = None,
        limit: int | None = None,
        continue_token: str | None = None,
        version_match: VersionMatch | None = None,
        resource_version: str | None = None,
    ) -> None:
        self.label_selector = label_selector
        self.field_selector = field_selector
        self.timeout = timeout
        self.limit = limit
        self.continue_token = continue_token
        self.version_match = version_match
        self.resource_version = resource_version

    def as_query_params(self) -> dict[str, str] | None:
        query_params = {}
        if self.label_selector is not None:
            query_params["labelSelector"] = self.label_selector
        if self.field_selector is not None:
            query_params["fieldSelector"] = self.field_selector
        if self.timeout is not None:
            query_params["timeoutSeconds"] = str(self.timeout)
        if self.limit is not None:
            query_params["limit"] = str(self.limit)
        if self.continue_token is not None:
            query_params["continue"] = self.continue_token
        if self.version_match is not None:
            query_params["resourceVersion"] = self.version_match.value
        if self.resource_version is not None:
            query_params["resourceVersion"] = self.resource_version
        return query_params or None


class WatchOptions:
    def __init__(
        self,
        label_selector: str | None = None,
        field_selector: str | None = None,
        allow_bookmarks: bool | None = None,
        send_initial_events: bool | None = None,
        timeout_seconds: int | None = None,
        resource_version: str | None = None,
    ) -> None:
        self.resource_version = resource_version
        self.label_selector = label_selector
        self.field_selector = field_selector
        self.allow_bookmarks = allow_bookmarks
        self.send_initial_events = send_initial_events
        self.timeout_seconds = timeout_seconds

    def as_query_params(self) -> dict[str, str]:
        query_params = {"watch": "true"}
        if self.label_selector is not None:
            query_params["labelSelector"] = self.label_selector
        if self.field_selector is not None:
            query_params["fieldSelector"] = self.field_selector
        if self.allow_bookmarks is not None:
            query_params["allowBookmarks"] = str(self.allow_bookmarks)
        if self.send_initial_events is not None:
            query_params["sendInitialEvents"] = str(self.send_initial_events)
        if self.timeout_seconds is not None:
            query_params["timeoutSeconds"] = str(self.timeout_seconds)
        return query_params


class GetOptions:
    def __init__(
        self,
        resource_version: str | None = None,
    ) -> None:
        self.resource_version = resource_version

    def as_query_params(self) -> dict[str, str] | None:
        if self.resource_version is None:
            return None
        return {"resourceVersion": self.resource_version}


class PostOptions:
    def __init__(
        self,
        dry_run: bool | None = None,
        field_manager: str | None = None,
    ) -> None:
        self.dry_run = dry_run
        self.field_manager = field_manager

    def as_query_params(self) -> dict[str, str] | None:
        query_params = {}
        if self.dry_run is not None:
            query_params["dryRun"] = str(self.dry_run)
        if self.field_manager is not None:
            query_params["fieldManager"] = self.field_manager
        return query_params or None


class PatchOptions:
    def __init__(
        self,
        dry_run: bool | None = None,
        field_manager: str | None = None,
        force: bool | None = None,
        field_validation: FieldValidation | None = None,
    ) -> None:
        self.dry_run = dry_run
        self.field_manager = field_manager
        self.force = force
        self.field_validation = field_validation

    def as_query_params(self) -> dict[str, str] | None:
        query_params = {}
        if self.dry_run is not None:
            query_params["dryRun"] = str(self.dry_run)
        if self.field_manager is not None:
            query_params["fieldManager"] = self.field_manager
        if self.force is not None:
            query_params["force"] = str(self.force)
        if self.field_validation is not None:
            query_params["fieldValidation"] = self.field_validation.value
        return query_params or None


class DeleteOptions:
    def __init__(
        self,
        dry_run: bool | None = None,
        grace_period_seconds: int | None = None,
        propagation_policy: PropagationPolicy | None = None,
        preconditions: Precondition | None = None,
    ) -> None:
        self.dry_run = dry_run
        self.grace_period_seconds = grace_period_seconds
        self.propagation_policy = propagation_policy
        self.preconditions = preconditions

    @classmethod
    def default(cls) -> DeleteOptions:
        return cls()

    def as_request_body(self) -> dict[str, Any] | None:
        body: dict[str, Any] = {}
        if self.dry_run is not None:
            body["dryRun"] = str(self.dry_run)
        if self.grace_period_seconds is not None:
            body["gracePeriodSeconds"] = str(self.grace_period_seconds)
        if self.propagation_policy is not None:
            body["propagationPolicy"] = self.propagation_policy.value
        if self.preconditions is not None:
            if self.preconditions.resource_version is not None:
                body["preconditions"] = {
                    "resourceVersion": self.preconditions.resource_version
                }
            if self.preconditions.uid is not None:
                body["preconditions"] = {"uid": self.preconditions.uid}
        return body or None


class PatchTypes(str, Enum):
    APPLY_PATCH = "ApplyPatch"
    JSON_PATCH = "JsonPatch"
    MERGE_PATCH = "MergePatch"
    STRATEGIC_MERGE_PATCH = "StrategicMergePatch"


PATCH_HEADERS = {
    PatchTypes.APPLY_PATCH: "application/apply-patch+yaml",
    PatchTypes.JSON_PATCH: "application/json-patch+json",
    PatchTypes.MERGE_PATCH: "application/merge-patch+json",
    PatchTypes.STRATEGIC_MERGE_PATCH: "application/strategic-merge-patch+json",
}


class ApplyPatch(Generic[ResourceType]):
    content_type_header: ClassVar[str] = "application/apply-patch+yaml"

    def __init__(self, body: ResourceType) -> None:
        self.body = body


class MergePatch(Generic[ResourceType]):
    content_type_header: ClassVar[str] = "application/merge-patch+json"

    def __init__(self, body: ResourceType) -> None:
        self.body = body


class StrategicMergePatch(Generic[ResourceType]):
    content_type_header: ClassVar[str] = "application/strategic-merge-patch+json"

    def __init__(self, body: ResourceType) -> None:
        self.body = body


class JsonPatch:
    content_type_header: ClassVar[str] = "application/json-patch+json"

    def __init__(self, body: list[dict[str, Any]]) -> None:
        self.body = body


class Req:
    def __init__(
        self,
        method: str,
        url: str,
        query_params: dict[str, str] | None = None,
        body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.url = url
        self.query_params = query_params
        self.method = method
        self.body = body
        self.headers = headers


class Request:
    def __init__(self, url: str) -> None:
        self.url = url

    def get(self, name: str, options: GetOptions) -> Req:
        query_params = options.as_query_params()
        return Req(
            method="GET",
            url=f"{self.url}/{name}",
            query_params=query_params,
        )

    def list(self, options: ListOptions) -> Req:
        query_params = options.as_query_params()
        return Req(
            method="GET",
            url=self.url,
            query_params=query_params,
        )

    def create(self, options: PostOptions) -> Req:
        query_params = options.as_query_params()
        return Req(
            method="POST",
            url=self.url,
            query_params=query_params,
        )

    def delete(self, name: str, options: DeleteOptions) -> Req:
        body = options.as_request_body()
        return Req(
            method="DELETE",
            url=f"{self.url}/{name}",
            body=body,
        )

    def delete_collection(
        self, options: ListOptions, delete_options: DeleteOptions
    ) -> Req:
        query_params = options.as_query_params()
        body = delete_options.as_request_body()
        return Req(
            method="DELETE",
            url=self.url,
            query_params=query_params,
            body=body,
        )

    def patch(self, name: str, patch_type: PatchTypes, options: PatchOptions) -> Req:
        header = PATCH_HEADERS.get(patch_type)
        if header is None:
            raise ValueError(f"Unsupported patch type: {patch_type}")
        query_params = options.as_query_params()
        return Req(
            method="PATCH",
            url=f"{self.url}/{name}",
            query_params=query_params,
            headers={"Content-Type": PATCH_HEADERS[patch_type]},
        )

    def replace(self, name: str, data: ResourceType, options: PostOptions) -> Req:
        query_params = options.as_query_params()
        return Req(
            method="PUT",
            url=f"{self.url}/{name}",
            query_params=query_params,
            body=data.dict(),
        )

    def watch(self, options: WatchOptions, resource_version: str | None = None) -> Req:
        query_params = options.as_query_params()
        if resource_version is not None:
            query_params["resourceVersion"] = resource_version
        return Req(
            method="GET",
            url=self.url,
            query_params=query_params,
        )


class ClientConfiguration:
    def __init__(self) -> None:
        self.namespace = "default"


class Client:
    def __init__(self) -> None:
        self.configuration = ClientConfiguration()


class Api(Generic[ResourceType]):
    request: Request
    client: Client
    namespace: str | None
    resource: Type[ResourceType]

    @classmethod
    def all(cls: Type[Self], client: Client, resource: Type[ResourceType]) -> Self:
        api: Self = cls()
        api.request = Request(url=resource.__RESOURCE_CONFIG__.url())
        api.client = client
        api.namespace = None
        api.resource = resource
        return api

    @classmethod
    def namespaced(
        cls: Type[Self], client: Client, resource: Type[ResourceType], namespace: str
    ) -> Self:
        api: Self = cls()
        api.request = Request(url=resource.__RESOURCE_CONFIG__.url(namespace=namespace))
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
        request = self.request.get(name, options)
        async with httpx.AsyncClient(**CLIENT_PARAMS) as client:
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
        request = self.request.list(options)
        async with httpx.AsyncClient(**CLIENT_PARAMS) as client:
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
        request = self.request.create(options)
        async with httpx.AsyncClient(**CLIENT_PARAMS) as client:
            response = await client.post(request.url, json=data.dict())
            response.raise_for_status()
            return cast(ResourceType, self.resource.model_validate(response.json()))

    # TODO: Status is also possible to return
    async def delete(
        self, name: str, options: DeleteOptions | None = None
    ) -> ResourceType:
        if options is None:
            options = DeleteOptions.default()
        request = self.request.delete(name, options)
        async with httpx.AsyncClient(**CLIENT_PARAMS) as client:
            response = await client.request(
                method="DELETE", url=request.url, json=request.body
            )
            response.raise_for_status()
            return cast(ResourceType, self.resource.model_validate(response.json()))

    # TODO: Status is also possible to return
    async def delete_collection(
        self, list_options: ListOptions, delete_options: DeleteOptions
    ) -> ListEntity[ResourceType]:
        request = self.request.delete_collection(list_options, delete_options)
        async with httpx.AsyncClient(**CLIENT_PARAMS) as client:
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

        request = self.request.patch(name, patch_type, options)
        async with httpx.AsyncClient(**CLIENT_PARAMS) as client:
            response = await client.patch(
                url=request.url, content=body, headers=request.headers
            )
            response.raise_for_status()
            return cast(ResourceType, self.resource.model_validate(response.json()))

    async def replace(
        self, name: str, data: ResourceType, options: PostOptions
    ) -> ResourceType:
        request = self.request.replace(name, data, options)
        async with httpx.AsyncClient(**CLIENT_PARAMS) as client:
            response = await client.put(request.url, json=request.body)
            response.raise_for_status()
            return cast(ResourceType, self.resource.model_validate(response.json()))

    async def watch(
        self, options: WatchOptions, resource_version: str | None = None
    ) -> AsyncGenerator[WatchEvent[ResourceType], None]:
        query_params = options.as_query_params()
        request = self.request.watch(options, resource_version=resource_version)
        async with httpx.AsyncClient(**CLIENT_PARAMS) as client:
            async with client.stream(
                "GET", request.url, params=query_params
            ) as response:
                response.raise_for_status()
                async for chunk in response.aiter_lines():
                    yield WatchEvent(self.resource, json.loads(chunk))
