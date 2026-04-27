from __future__ import annotations

from types import EllipsisType

from kubex.core.params import (
    AttachOptions,
    NamespaceTypes,
    TimeoutTypes,
)
from kubex.core.request import Request
from kubex.core.request_builder.subresource import RequestBuilderProtocol
from kubex_core.models.resource_config import Scope


class AttachRequestBuilder(RequestBuilderProtocol):
    def attach_request(
        self,
        name: str,
        namespace: NamespaceTypes,
        options: AttachOptions,
        *,
        request_timeout: TimeoutTypes | EllipsisType = ...,
    ) -> Request:
        if self.resource_config.scope == Scope.CLUSTER:
            raise ValueError("attach is only valid for namespace-scoped resources")
        if namespace is None:
            raise ValueError("namespace is required for attach")
        return Request(
            method="GET",
            url=f"{self.resource_config.url(namespace, name)}/attach",
            query_param_pairs=options.to_query_params(),
            timeout=request_timeout,
        )
