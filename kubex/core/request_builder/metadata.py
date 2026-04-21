from types import EllipsisType

from kubex.core.params import (
    GetOptions,
    ListOptions,
    NamespaceTypes,
    PatchOptions,
    TimeoutTypes,
    WatchOptions,
)
from kubex.core.patch import Patch
from kubex.core.request import Request
from kubex.core.request_builder.constants import (
    ACCEPT_HEADER,
    APPLICATION_JSON_MIME_TYPE,
    CONTENT_TYPE_HEADER,
    METADATA_LIST_MIME_TYPE,
    METADATA_MIME_TYPE,
)
from kubex.core.request_builder.subresource import RequestBuilderProtocol


class MetadataRequestBuilder(RequestBuilderProtocol):
    def get_metadata(
        self,
        name: str,
        namespace: NamespaceTypes,
        options: GetOptions,
        *,
        request_timeout: TimeoutTypes | EllipsisType = ...,
    ) -> Request:
        query_params = options.as_query_params()
        headers = {
            ACCEPT_HEADER: METADATA_MIME_TYPE,
            CONTENT_TYPE_HEADER: APPLICATION_JSON_MIME_TYPE,
        }
        return Request(
            method="GET",
            url=self.resource_config.url(namespace, name),
            query_params=query_params,
            headers=headers,
            timeout=request_timeout,
        )

    def list_metadata(
        self,
        namespace: NamespaceTypes,
        options: ListOptions,
        *,
        request_timeout: TimeoutTypes | EllipsisType = ...,
    ) -> Request:
        query_params = options.as_query_params()
        headers = {
            ACCEPT_HEADER: METADATA_LIST_MIME_TYPE,
            CONTENT_TYPE_HEADER: APPLICATION_JSON_MIME_TYPE,
        }
        return Request(
            method="GET",
            url=self.resource_config.url(namespace),
            query_params=query_params,
            headers=headers,
            timeout=request_timeout,
        )

    def watch_metadata(
        self,
        namespace: NamespaceTypes,
        options: WatchOptions,
        resource_version: str | None = None,
        *,
        request_timeout: TimeoutTypes | EllipsisType = ...,
    ) -> Request:
        query_params = options.as_query_params()
        if resource_version is not None:
            query_params["resourceVersion"] = resource_version
        headers = {
            ACCEPT_HEADER: APPLICATION_JSON_MIME_TYPE,
            CONTENT_TYPE_HEADER: METADATA_MIME_TYPE,
        }
        return Request(
            method="GET",
            url=self.resource_config.url(namespace),
            query_params=query_params,
            headers=headers,
            timeout=request_timeout,
        )

    def patch_metadata(
        self,
        name: str,
        namespace: NamespaceTypes,
        options: PatchOptions,
        patch: Patch,
        *,
        request_timeout: TimeoutTypes | EllipsisType = ...,
    ) -> Request:
        return Request(
            method="PATCH",
            url=self.resource_config.url(namespace, name),
            query_params=options.as_query_params(),
            headers={
                ACCEPT_HEADER: METADATA_MIME_TYPE,
                CONTENT_TYPE_HEADER: patch.content_type_header,
            },
            body=patch.serialize(),
            timeout=request_timeout,
        )
