from typing import Any, Self

from kubex.core.params import (
    DeleteOptions,
    GetOptions,
    ListOptions,
    PatchOptions,
    PostOptions,
    WatchOptions,
)
from kubex.core.patch import PATCH_HEADERS, PatchTypes
from kubex.core.request import Request
from kubex.core.request_builder.logs import LogsRequestBuilder
from kubex.core.request_builder.metadata import MetadataRequestBuilder
from kubex.models.base import ResourceConfig


class RequestBuilder(MetadataRequestBuilder, LogsRequestBuilder):
    def __init__(self, resource_config: ResourceConfig[Any]) -> None:
        self.resource_config = resource_config
        self._namespace: str | None = None

    @property
    def namespace(self) -> str | None:
        return self._namespace

    @namespace.setter
    def namespace(self, namespace: str | None) -> None:
        self._namespace = namespace

    def with_namespace(self, namespace: str) -> Self:
        self.namespace = namespace
        return self

    def without_namespace(self) -> Self:
        self.namespace = None
        return self

    def get(self, name: str, options: GetOptions) -> Request:
        query_params = options.as_query_params()
        return Request(
            method="GET",
            url=self.resource_config.url(self._namespace, name),
            query_params=query_params,
        )

    def list(self, options: ListOptions) -> Request:
        query_params = options.as_query_params()
        return Request(
            method="GET",
            url=self.resource_config.url(self._namespace),
            query_params=query_params,
        )

    def create(self, options: PostOptions) -> Request:
        query_params = options.as_query_params()
        return Request(
            method="POST",
            url=self.resource_config.url(self._namespace),
            query_params=query_params,
        )

    def delete(self, name: str, options: DeleteOptions) -> Request:
        body = options.as_request_body()
        return Request(
            method="DELETE",
            url=self.resource_config.url(self._namespace, name),
            body=body,
        )

    def delete_collection(
        self, options: ListOptions, delete_options: DeleteOptions
    ) -> Request:
        query_params = options.as_query_params()
        body = delete_options.as_request_body()
        return Request(
            method="DELETE",
            url=self.resource_config.url(self._namespace),
            query_params=query_params,
            body=body,
        )

    def patch(
        self, name: str, patch_type: PatchTypes, options: PatchOptions
    ) -> Request:
        patch_header = PATCH_HEADERS.get(patch_type)
        if patch_header is None:
            raise ValueError(f"Unsupported patch type: {patch_type}")
        query_params = options.as_query_params()
        return Request(
            method="PATCH",
            url=self.resource_config.url(self._namespace, name),
            query_params=query_params,
            headers={"Content-Type": patch_header},
        )

    def replace(self, name: str, options: PostOptions) -> Request:
        query_params = options.as_query_params()
        return Request(
            method="PUT",
            url=self.resource_config.url(self._namespace, name),
            query_params=query_params,
        )

    def watch(
        self, options: WatchOptions, resource_version: str | None = None
    ) -> Request:
        query_params = options.as_query_params()
        if resource_version is not None:
            query_params["resourceVersion"] = resource_version
        return Request(
            method="GET",
            url=self.resource_config.url(self._namespace),
            query_params=query_params,
        )

    # def logs(self, name: str, options: LogOptions) -> Request:
    #     query_params = options.as_query_params()
    #     return Request(
    #         method="GET",
    #         url=f"{self.resource_config.url(self._namespace, name)}/log",
    #         query_params=query_params,
    #     )

    # def stream_logs(self, name: str, options: LogOptions) -> Request:
    #     query_params = options.as_query_params()
    #     if query_params is None:
    #         query_params = {"follow": "true"}
    #     else:
    #         query_params["follow"] = "true"
    #     return Request(
    #         method="GET",
    #         url=f"{self.resource_config.url(self._namespace, name)}/log",
    #         query_params=query_params,
    #     )
