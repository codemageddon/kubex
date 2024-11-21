from typing import AsyncGenerator

from kubex.core.params import LogOptions
from kubex.models.interfaces import HasLogs
from kubex.models.typing import ResourceType

from ._protocol import ApiNamespaceTypes, ApiProtocol


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

    async def logs(
        self,
        name: str,
        *,
        namespace: ApiNamespaceTypes = Ellipsis,
        container: str | None = None,
        limit_bytes: int | None = None,
        pretty: bool | None = None,
        previous: bool | None = None,
        since_seconds: int | None = None,
        tail_lines: int | None = None,
        timestamps: bool | None = None,
    ) -> str:
        self._check_implemented()
        _namespace = self._ensure_required_namespace(namespace)
        options = LogOptions(
            container=container,
            limit_bytes=limit_bytes,
            pretty=pretty,
            previous=previous,
            since_seconds=since_seconds,
            tail_lines=tail_lines,
            timestamps=timestamps,
        )
        request = self._request_builder.logs(name, _namespace, options=options)
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
        self,
        name: str,
        namespace: ApiNamespaceTypes = Ellipsis,
        container: str | None = None,
        limit_bytes: int | None = None,
        pretty: bool | None = None,
        previous: bool | None = None,
        since_seconds: int | None = None,
        tail_lines: int | None = None,
        timestamps: bool | None = None,
        options: LogOptions | None = None,
    ) -> AsyncGenerator[str, None]:
        self._check_implemented()
        _namespace = self._ensure_required_namespace(namespace)
        options = LogOptions(
            container=container,
            limit_bytes=limit_bytes,
            pretty=pretty,
            previous=previous,
            since_seconds=since_seconds,
            tail_lines=tail_lines,
            timestamps=timestamps,
        )
        request = self._request_builder.stream_logs(name, _namespace, options=options)
        # TODO: ReadTimeout
        async for line in self._client.stream_lines(request):
            yield line
