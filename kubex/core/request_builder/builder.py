from typing import Any

from kubex.core.params import (
    DeleteOptions,
    GetOptions,
    ListOptions,
    PatchOptions,
    PostOptions,
    WatchOptions,
)
from kubex.core.patch import Patch
from kubex.core.request import Request
from kubex.core.request_builder.logs import LogsRequestBuilder
from kubex.core.request_builder.metadata import MetadataRequestBuilder
from kubex.models.resource_config import ResourceConfig

from .constants import ACCEPT_HEADER, APPLICATION_JSON_MIME_TYPE, CONTENT_TYPE_HEADER
from .subresource import SubresourceRequestBuilder


class RequestBuilder(
    MetadataRequestBuilder, SubresourceRequestBuilder, LogsRequestBuilder
):
    def __init__(self, resource_config: ResourceConfig[Any]) -> None:
        self.resource_config = resource_config

    def get(self, name: str, namespace: str | None, options: GetOptions) -> Request:
        query_params = options.as_query_params()
        return Request(
            method="GET",
            url=self.resource_config.url(namespace, name),
            query_params=query_params,
        )

    def list(self, namespace: str | None, options: ListOptions) -> Request:
        query_params = options.as_query_params()
        return Request(
            method="GET",
            url=self.resource_config.url(namespace),
            query_params=query_params,
        )

    def create(
        self, namespace: str | None, options: PostOptions, data: str | bytes
    ) -> Request:
        query_params = options.as_query_params()
        return Request(
            method="POST",
            url=self.resource_config.url(namespace),
            query_params=query_params,
            body=data,
        )

    def delete(
        self, name: str, namespace: str | None, options: DeleteOptions
    ) -> Request:
        body = options.as_request_body()
        return Request(
            method="DELETE",
            url=self.resource_config.url(namespace, name),
            body=body,
        )

    def delete_collection(
        self, namespace: str | None, options: ListOptions, delete_options: DeleteOptions
    ) -> Request:
        query_params = options.as_query_params()
        body = delete_options.as_request_body()
        return Request(
            method="DELETE",
            url=self.resource_config.url(namespace),
            query_params=query_params,
            body=body,
        )

    def patch(
        self, name: str, namespace: str | None, options: PatchOptions, patch: Patch
    ) -> Request:
        return Request(
            method="PATCH",
            url=self.resource_config.url(namespace, name),
            body=patch.serialize(by_alias=True, exclude_unset=True),
            query_params=options.as_query_params(),
            headers={
                ACCEPT_HEADER: APPLICATION_JSON_MIME_TYPE,
                CONTENT_TYPE_HEADER: patch.content_type_header,
            },
        )

    def replace(
        self, name: str, namespace: str | None, options: PostOptions, data: str | bytes
    ) -> Request:
        query_params = options.as_query_params()
        return Request(
            method="PUT",
            url=self.resource_config.url(namespace, name),
            query_params=query_params,
            body=data,
        )

    def watch(
        self,
        namespace: str | None,
        options: WatchOptions,
        resource_version: str | None = None,
    ) -> Request:
        query_params = options.as_query_params()
        if resource_version is not None:
            query_params["resourceVersion"] = resource_version
        return Request(
            method="GET",
            url=self.resource_config.url(namespace),
            query_params=query_params,
        )
