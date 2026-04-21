from types import EllipsisType

from kubex.core.params import (
    LogOptions,
    NamespaceTypes,
    TimeoutTypes,
)
from kubex.core.request import Request
from kubex.core.request_builder.subresource import RequestBuilderProtocol


class LogsRequestBuilder(RequestBuilderProtocol):
    def logs(
        self,
        name: str,
        namespace: NamespaceTypes,
        options: LogOptions,
        *,
        request_timeout: TimeoutTypes | EllipsisType = ...,
    ) -> Request:
        query_params = options.as_query_params()
        return Request(
            method="GET",
            url=f"{self.resource_config.url(namespace, name)}/log",
            query_params=query_params,
            timeout=request_timeout,
        )

    def stream_logs(
        self,
        name: str,
        namespace: NamespaceTypes,
        options: LogOptions,
        *,
        request_timeout: TimeoutTypes | EllipsisType = ...,
    ) -> Request:
        query_params = options.as_query_params()
        if query_params is None:
            query_params = {"follow": "true"}
        else:
            query_params["follow"] = "true"
        return Request(
            method="GET",
            url=f"{self.resource_config.url(namespace, name)}/log",
            query_params=query_params,
            timeout=request_timeout,
        )
