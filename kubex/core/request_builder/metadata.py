from kubex.core.params import GetOptions, ListOptions, PatchOptions, WatchOptions
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
    def get_metadata(self, name: str, options: GetOptions) -> Request:
        query_params = options.as_query_params()
        headers = {
            ACCEPT_HEADER: METADATA_MIME_TYPE,
            CONTENT_TYPE_HEADER: APPLICATION_JSON_MIME_TYPE,
        }
        return Request(
            method="GET",
            url=self.resource_config.url(self.namespace, name),
            query_params=query_params,
            headers=headers,
        )

    def list_metadata(self, options: ListOptions) -> Request:
        query_params = options.as_query_params()
        headers = {
            ACCEPT_HEADER: METADATA_LIST_MIME_TYPE,
            CONTENT_TYPE_HEADER: APPLICATION_JSON_MIME_TYPE,
        }
        return Request(
            method="GET",
            url=self.resource_config.url(self.namespace),
            query_params=query_params,
            headers=headers,
        )

    def watch_metadata(
        self, options: WatchOptions, resource_version: str | None = None
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
            url=self.resource_config.url(self.namespace),
            query_params=query_params,
            headers=headers,
        )

    def patch_metadata(self, name: str, options: PatchOptions, patch: Patch) -> Request:
        return Request(
            method="PATCH",
            url=self.resource_config.url(self.namespace, name),
            query_params=options.as_query_params(),
            headers={
                ACCEPT_HEADER: METADATA_MIME_TYPE,
                CONTENT_TYPE_HEADER: patch.content_type_header,
            },
            body=patch.serialize(),
        )
