from __future__ import annotations

import typing
from weakref import ref

from kubex.models.base import ResourceConfig

if typing.TYPE_CHECKING:
    from kubex.core.request_builder.builder import RequestBuilder


class BaseSubresourceRequestBuilder:
    def __init__(self, request_builder_ref: ref[RequestBuilder]) -> None:
        self.request_builder = request_builder_ref
        request_builder = self.request_builder()
        if request_builder is None:
            raise RuntimeError("RequestBuilder has been garbage collected")
        self.resource_config = request_builder.resource_config

    @property
    def namespace(self) -> str | None:
        request_builder = self.request_builder()
        if request_builder is None:
            raise RuntimeError("RequestBuilder has been garbage collected")
        return request_builder.namespace


class RequestBuilderProtocol(typing.Protocol):
    _namespace: str | None = None
    resource_config: ResourceConfig[typing.Any]

    @property
    def namespace(self) -> str | None: ...
