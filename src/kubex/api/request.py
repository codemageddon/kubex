from typing import Any

from kubex.api.params import (
    DeleteOptions,
    GetOptions,
    ListOptions,
    PatchOptions,
    PostOptions,
    WatchOptions,
)
from kubex.api.patch import PATCH_HEADERS, PatchTypes


class Request:
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


class RequestBuilder:
    def __init__(self, url: str) -> None:
        self.url = url

    def get(self, name: str, options: GetOptions) -> Request:
        query_params = options.as_query_params()
        return Request(
            method="GET",
            url=f"{self.url}/{name}",
            query_params=query_params,
        )

    def list(self, options: ListOptions) -> Request:
        query_params = options.as_query_params()
        return Request(
            method="GET",
            url=self.url,
            query_params=query_params,
        )

    def create(self, options: PostOptions) -> Request:
        query_params = options.as_query_params()
        return Request(
            method="POST",
            url=self.url,
            query_params=query_params,
        )

    def delete(self, name: str, options: DeleteOptions) -> Request:
        body = options.as_request_body()
        return Request(
            method="DELETE",
            url=f"{self.url}/{name}",
            body=body,
        )

    def delete_collection(
        self, options: ListOptions, delete_options: DeleteOptions
    ) -> Request:
        query_params = options.as_query_params()
        body = delete_options.as_request_body()
        return Request(
            method="DELETE",
            url=self.url,
            query_params=query_params,
            body=body,
        )

    def patch(
        self, name: str, patch_type: PatchTypes, options: PatchOptions
    ) -> Request:
        header = PATCH_HEADERS.get(patch_type)
        if header is None:
            raise ValueError(f"Unsupported patch type: {patch_type}")
        query_params = options.as_query_params()
        return Request(
            method="PATCH",
            url=f"{self.url}/{name}",
            query_params=query_params,
            headers={"Content-Type": PATCH_HEADERS[patch_type]},
        )

    def replace(self, name: str, options: PostOptions) -> Request:
        query_params = options.as_query_params()
        return Request(
            method="PUT",
            url=f"{self.url}/{name}",
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
            url=self.url,
            query_params=query_params,
        )
