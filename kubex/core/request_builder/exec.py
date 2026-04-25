from __future__ import annotations

from types import EllipsisType

from kubex.core.params import (
    ExecOptions,
    NamespaceTypes,
    TimeoutTypes,
)
from kubex.core.request import Request
from kubex.core.request_builder.subresource import RequestBuilderProtocol
from kubex_core.models.resource_config import Scope


class ExecRequestBuilder(RequestBuilderProtocol):
    def exec_request(
        self,
        name: str,
        namespace: NamespaceTypes,
        options: ExecOptions,
        *,
        request_timeout: TimeoutTypes | EllipsisType = ...,
    ) -> Request:
        if self.resource_config.scope == Scope.CLUSTER:
            raise ValueError("exec is only valid for namespace-scoped resources")
        if namespace is None:
            raise ValueError("namespace is required for exec")
        return Request(
            method="GET",
            url=f"{self.resource_config.url(namespace, name)}/exec",
            query_param_pairs=options.to_query_params(),
            timeout=request_timeout,
        )
