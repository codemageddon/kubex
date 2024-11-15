from __future__ import annotations

import typing

from kubex.core.params import PatchOptions, PostOptions
from kubex.core.patch import Patch
from kubex.core.request import Request
from kubex.models.resource_config import ResourceConfig

from .constants import ACCEPT_HEADER, CONTENT_TYPE_HEADER

if typing.TYPE_CHECKING:
    pass


class RequestBuilderProtocol(typing.Protocol):
    _namespace: str | None = None
    resource_config: ResourceConfig[typing.Any]

    @property
    def namespace(self) -> str | None: ...


class SubresourceRequestBuilder(RequestBuilderProtocol):
    def get_subresource(self, subresource: str, name: str) -> Request:
        return Request(
            method="GET",
            url=self.resource_config.url(self.namespace, name) + f"/{subresource}",
        )

    def replace_subresource(
        self, subresource: str, name: str, data: bytes | str, options: PostOptions
    ) -> Request:
        return Request(
            method="PUT",
            url=self.resource_config.url(self.namespace, name) + f"/{subresource}",
            body=data,
            query_params=options.as_query_params(),
        )

    def patch_subresource(
        self, subresource: str, name: str, options: PatchOptions, patch: Patch
    ) -> Request:
        return Request(
            method="PATCH",
            url=self.resource_config.url(self.namespace, name) + f"/{subresource}",
            body=patch.serialize(),
            headers={
                ACCEPT_HEADER: "application/json",
                CONTENT_TYPE_HEADER: patch.content_type_header,
            },
            query_params=options.as_query_params(),
        )
