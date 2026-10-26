from __future__ import annotations

from datetime import datetime
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
        since_time: datetime | None = None,
        tail_lines: int | None = None,
        timestamps: bool | None = None,
        request_timeout: ApiRequestTimeoutTypes = Ellipsis,
    ) -> str:
        """Read logs of the specified resource.

        ``since_seconds`` and ``since_time`` (a timezone-aware datetime, sent as
        an RFC 3339 UTC ``sinceTime``) are mutually exclusive.

        Args:
            name: The name of the resource to read logs of.
            namespace: The namespace of the namespaced resource. If not provided,
                the namespace provided when creating the API will be used.
                The namespace is required for namespaced resources.
                If namespace is provided for cluster-scoped resources, an error will be raised.
            container: The container to read logs of. Required when the Pod has
                more than one container; the API server rejects the request otherwise.
            limit_bytes: The maximum number of bytes of log output to return.
            pretty: Ask the API server to pretty-print the output.
            previous: Return logs of the previous, terminated instance of the
                container (e.g. after a crash).
            since_seconds: Only return logs newer than this many seconds.
            since_time: Only return logs newer than this timezone-aware instant.
                A naive datetime raises ``ValueError``.
            tail_lines: Only return this many lines from the end of the log.
            timestamps: Prefix each line with its RFC 3339 timestamp.
            request_timeout: HTTP-level timeout override for this call. A number is
                interpreted as the total timeout in seconds. Pass ``None`` to disable
                timeouts entirely for this call. Omit to use the client default.

        Returns:
            str: the log output, decoded as text.

        Raises:
            ValueError: an argument is invalid, e.g. an empty or malformed ``name``,
                or a namespace that is missing for a namespace-scoped resource or
                given for a cluster-scoped one; or both
                ``since_seconds`` and ``since_time`` are given, or ``since_time`` is a
                naive datetime.
            BadRequest: the API server rejected the arguments, e.g. ``container``
                was not given for a pod with several containers.
            NotFound: the pod does not exist.
            KubexApiError: the API server rejected the request; the subclass
                matches the HTTP status (e.g. ``Forbidden``, ``UnprocessableEntity``).
            KubexConnectionError: the API server could not be reached.
            KubexTimeoutError: the request timed out on the client side.
            ConfigurationError: credentials could not be obtained, e.g. an exec
                plugin or OIDC token refresh failed.
        """
        _namespace = ensure_required_namespace(namespace, self._namespace, self._scope)
        options = LogOptions(
            container=container,
            limit_bytes=limit_bytes,
            pretty=pretty,
            previous=previous,
            since_seconds=since_seconds,
            since_time=since_time,
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
        since_time: datetime | None = None,
        tail_lines: int | None = None,
        timestamps: bool | None = None,
        request_timeout: ApiRequestTimeoutTypes = Ellipsis,
    ) -> AsyncGenerator[str, None]:
        """Stream logs of the specified resource.

        Follows the log (``follow=true``): the stream continues until the
        container exits or the caller stops iterating. ``since_seconds`` and
        ``since_time`` (a timezone-aware datetime, sent as an RFC 3339 UTC
        ``sinceTime``) are mutually exclusive.

        Args:
            name: The name of the resource to stream logs of.
            namespace: The namespace of the namespaced resource. If not provided,
                the namespace provided when creating the API will be used.
                The namespace is required for namespaced resources.
                If namespace is provided for cluster-scoped resources, an error will be raised.
            container: The container to stream logs of. Required when the Pod has
                more than one container; the API server rejects the request otherwise.
            limit_bytes: The maximum number of bytes of log output to return.
            pretty: Ask the API server to pretty-print the output.
            previous: Return logs of the previous, terminated instance of the
                container (e.g. after a crash).
            since_seconds: Only return logs newer than this many seconds.
            since_time: Only return logs newer than this timezone-aware instant,
                e.g. the timestamp of the last line processed before a reconnect.
                A naive datetime raises ``ValueError``.
            tail_lines: Start with only this many lines from the end of the log.
            timestamps: Prefix each line with its RFC 3339 timestamp.
            request_timeout: HTTP-level timeout override for this call. A number is
                interpreted as the total timeout in seconds. Pass ``None`` to disable
                timeouts entirely for this call. Omit to use the client's default
                for streams, which does not cut off an idle stream. An explicit
                short read/total timeout will terminate a quiet stream.

        Yields:
            str: one log line at a time, without the trailing newline.

        Raises:
            ValueError: an argument is invalid, e.g. an empty or malformed ``name``,
                or a namespace that is missing for a namespace-scoped resource or
                given for a cluster-scoped one; or both
                ``since_seconds`` and ``since_time`` are given, or ``since_time`` is a
                naive datetime.
            BadRequest: the API server rejected the arguments, e.g. ``container``
                was not given for a pod with several containers.
            NotFound: the pod does not exist.
            KubexApiError: the API server rejected the request; the subclass
                matches the HTTP status (e.g. ``Forbidden``, ``UnprocessableEntity``).
            KubexConnectionError: the API server could not be reached, or the
                connection broke mid-stream.
            KubexTimeoutError: the request timed out on the client side, including
                mid-stream.
            ConfigurationError: credentials could not be obtained, e.g. an exec
                plugin or OIDC token refresh failed.
        """
        _namespace = ensure_required_namespace(namespace, self._namespace, self._scope)
        options = LogOptions(
            container=container,
            limit_bytes=limit_bytes,
            pretty=pretty,
            previous=previous,
            since_seconds=since_seconds,
            since_time=since_time,
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
