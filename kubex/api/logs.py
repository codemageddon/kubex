from typing import AsyncGenerator

from kubex.core.params import LogOptions
from kubex.models.base import HasLogs, ResourceType

from ._protocol import ApiProtocol


class LogsMixin(ApiProtocol[ResourceType]):
    def _check_implemented(self) -> None:
        if not issubclass(self._resource, HasLogs):
            raise NotImplementedError("Logs are only supported for Pods")

    # TODO: Investigate how to force mypy to complain on logs calling with non-Pod resources
    # @overload
    # def logs(
    #     self: Type[ApiProtocol[Any]],
    #     name: str,
    #     options: LogOptions | None = None,
    # ) -> NoReturn: ...

    # @overload
    # def logs(
    #     self: Type[ApiProtocol[PodProtocol]],
    #     name: str,
    #     options: LogOptions | None = None,
    # ) -> Awaitable[str]: ...

    async def logs(self, name: str, options: LogOptions | None = None) -> str:
        self._check_implemented()
        self._check_namespace()
        request = self._request_builder.logs(
            name, options=options or LogOptions.default()
        )
        async with self._client.get_client() as client:
            async with self._client.get_client() as client:
                response = await client.get(request.url, params=request.query_params)
                response.raise_for_status()
                return response.text

    # TODO: Investigate how to force mypy to complain on stream_logs calling with non-Pod resources
    # @overload
    # def stream_logs(
    #     self: Type[ApiProtocol[ResourceType]],
    #     name: str,
    #     options: LogOptions | None = None,
    # ) -> NoReturn: ...

    # @overload
    # def stream_logs(
    #     self: Type[ApiProtocol[PodProtocol]],
    #     name: str,
    #     options: LogOptions | None = None,
    # ) -> AsyncGenerator[str, None]: ...

    async def stream_logs(
        self, name: str, options: LogOptions | None = None
    ) -> AsyncGenerator[str, None]:
        self._check_implemented()
        self._check_namespace()
        request = self._request_builder.stream_logs(
            name, options=options or LogOptions.default()
        )
        # TODO: ReadTimeout
        async with self._client.get_client() as client:
            async with client.stream(
                "GET", request.url, params=request.query_params
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    yield line
