from kubex.core.params import GetOptions, ListOptions, PatchOptions, WatchOptions
from kubex.core.patch import PATCH_HEADERS, PatchTypes
from kubex.core.request import Request
from kubex.core.request_builder.subresource import RequestBuilderProtocol


class MetadataRequestBuilder(RequestBuilderProtocol):
    def get_metadata(self, name: str, options: GetOptions) -> Request:
        query_params = options.as_query_params()
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json;as=PartialObjectMetadata;g=meta.k8s.io;v=v1",
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
            "Accept": "application/json",
            "Content-Type": "application/json;as=PartialObjectMetadataList;g=meta.k8s.io;v=v1",
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
            "Accept": "application/json",
            "Content-Type": "application/json;as=PartialObjectMetadata;g=meta.k8s.io;v=v1",
        }
        return Request(
            method="GET",
            url=self.resource_config.url(self.namespace),
            query_params=query_params,
            headers=headers,
        )

    def patch_metadata(
        self, name: str, patch_type: PatchTypes, options: PatchOptions
    ) -> Request:
        patch_header = PATCH_HEADERS.get(patch_type)
        if patch_header is None:
            raise ValueError(f"Unsupported patch type: {patch_type}")
        query_params = options.as_query_params()
        headers = {
            "Accept": patch_header,
            "Content-Type": "application/json;as=PartialObjectMetadata;g=meta.k8s.io;v=v1",
        }
        return Request(
            method="PATCH",
            url=self.resource_config.url(self.namespace, name),
            query_params=query_params,
            headers=headers,
        )
