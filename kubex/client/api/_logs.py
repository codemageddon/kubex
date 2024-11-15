from typing import AsyncGenerator

from kubex.core.params import LogOptions
from kubex.models.interfaces import HasLogs
from kubex.models.typing import ResourceType

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
        response = await self._client.request(request)
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
        async for line in self._client.stream_lines(request):
            yield line
