from kubex.core.params import (
    LogOptions,
)
from kubex.core.request import Request
from kubex.core.request_builder.subresource import RequestBuilderProtocol


class LogsRequestBuilder(RequestBuilderProtocol):
    def logs(self, name: str, options: LogOptions) -> Request:
        query_params = options.as_query_params()
        return Request(
            method="GET",
            url=f"{self.resource_config.url(self.namespace, name)}/log",
            query_params=query_params,
        )

    def stream_logs(self, name: str, options: LogOptions) -> Request:
        query_params = options.as_query_params()
        if query_params is None:
            query_params = {"follow": "true"}
        else:
            query_params["follow"] = "true"
        return Request(
            method="GET",
            url=f"{self.resource_config.url(self.namespace, name)}/log",
            query_params=query_params,
        )
