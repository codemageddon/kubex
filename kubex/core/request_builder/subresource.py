from __future__ import annotations

import typing
from types import EllipsisType

from kubex.core.params import (
    NamespaceTypes,
    PatchOptions,
    PostOptions,
    TimeoutTypes,
)
from kubex.core.patch import Patch
from kubex.core.request import Request
from kubex_core.models.resource_config import ResourceConfig

from .constants import ACCEPT_HEADER, CONTENT_TYPE_HEADER

if typing.TYPE_CHECKING:
    pass


class RequestBuilderProtocol(typing.Protocol):
    _namespace: str | None = None
    resource_config: ResourceConfig[typing.Any]


class SubresourceRequestBuilder(RequestBuilderProtocol):
    def get_subresource(
        self,
        subresource: str,
        name: str,
        namespace: NamespaceTypes,
        *,
        request_timeout: TimeoutTypes | EllipsisType = ...,
    ) -> Request:
        return Request(
            method="GET",
            url=self.resource_config.url(namespace, name) + f"/{subresource}",
            timeout=request_timeout,
        )

    def replace_subresource(
        self,
        subresource: str,
        name: str,
        namespace: NamespaceTypes,
        data: bytes | str,
        options: PostOptions,
        *,
        request_timeout: TimeoutTypes | EllipsisType = ...,
    ) -> Request:
        return Request(
            method="PUT",
            url=self.resource_config.url(namespace, name) + f"/{subresource}",
            body=data,
            query_params=options.as_query_params(),
            timeout=request_timeout,
        )

    def create_subresource(
        self,
        subresource: str,
        name: str,
        namespace: NamespaceTypes,
        data: bytes | str,
        options: PostOptions,
        *,
        request_timeout: TimeoutTypes | EllipsisType = ...,
    ) -> Request:
        return Request(
            method="POST",
            url=self.resource_config.url(namespace, name) + f"/{subresource}",
            body=data,
            query_params=options.as_query_params(),
            timeout=request_timeout,
        )

    def patch_subresource(
        self,
        subresource: str,
        name: str,
        namespace: NamespaceTypes,
        options: PatchOptions,
        patch: Patch,
        *,
        request_timeout: TimeoutTypes | EllipsisType = ...,
    ) -> Request:
        return Request(
            method="PATCH",
            url=self.resource_config.url(namespace, name) + f"/{subresource}",
            body=patch.serialize(),
            headers={
                ACCEPT_HEADER: "application/json",
                CONTENT_TYPE_HEADER: patch.content_type_header,
            },
            query_params=options.as_query_params(),
            timeout=request_timeout,
        )
