from __future__ import annotations

from typing import Any, AsyncGenerator, Generic, Type, TypeVar, overload

from kubex.client.client import BaseClient
from kubex.core.params import LogOptions, NamespaceTypes
from kubex.core.request_builder.builder import RequestBuilder
from kubex_core.models.interfaces import HasLogs
from kubex_core.models.resource_config import Scope
from kubex_core.models.typing import ResourceType

from ._protocol import (
    ApiNamespaceTypes,
    ApiProtocol,
    ApiRequestTimeoutTypes,
    CachedSubresourceDescriptor,
    SubresourceNotAvailable,
    ensure_required_namespace,
)

_L = TypeVar("_L", bound=HasLogs)


class LogsAccessor(Generic[ResourceType]):
    """Accessor for logs subresource operations."""

    def __init__(
        self,
        client: BaseClient,
        request_builder: RequestBuilder,
        namespace: NamespaceTypes,
        scope: Scope,
        resource_type: Type[ResourceType],
    ) -> None:
        self._client = client
        self._request_builder = request_builder
        self._namespace = namespace
        self._scope = scope
        self._resource_type = resource_type

    async def get(
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
        request_timeout: ApiRequestTimeoutTypes = Ellipsis,
    ) -> str:
        """Read logs of the specified resource."""
        _namespace = ensure_required_namespace(namespace, self._namespace, self._scope)
        options = LogOptions(
            container=container,
            limit_bytes=limit_bytes,
            pretty=pretty,
            previous=previous,
            since_seconds=since_seconds,
            tail_lines=tail_lines,
            timestamps=timestamps,
        )
        request = self._request_builder.logs(
            name, _namespace, options=options, request_timeout=request_timeout
        )
        response = await self._client.request(request)
        return response.text

    async def stream(
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
        request_timeout: ApiRequestTimeoutTypes = Ellipsis,
    ) -> AsyncGenerator[str, None]:
        """Stream logs of the specified resource."""
        _namespace = ensure_required_namespace(namespace, self._namespace, self._scope)
        options = LogOptions(
            container=container,
            limit_bytes=limit_bytes,
            pretty=pretty,
            previous=previous,
            since_seconds=since_seconds,
            tail_lines=tail_lines,
            timestamps=timestamps,
        )
        request = self._request_builder.stream_logs(
            name, _namespace, options=options, request_timeout=request_timeout
        )
        async for line in self._client.stream_lines(request):
            yield line


class _LogsDescriptor(CachedSubresourceDescriptor):
    _marker = HasLogs
    _accessor_cls = LogsAccessor
    _error_message = "Logs are only supported for resources with HasLogs marker"

    @overload
    def __get__(self, instance: None, owner: type) -> _LogsDescriptor: ...

    @overload
    def __get__(self, instance: ApiProtocol[_L], owner: type) -> LogsAccessor[_L]: ...

    @overload
    def __get__(
        self, instance: ApiProtocol[Any], owner: type
    ) -> SubresourceNotAvailable: ...

    def __get__(self, instance: Any, owner: type | None = None) -> Any:
        return self._resolve(instance)
