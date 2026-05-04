from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Generic, Type, TypeVar, overload

from kubex.api._stream_session import StreamSession, _resolve_protocol
from kubex.client.client import BaseClient
from kubex.core.exec_channels import (
    DEFAULT_PROTOCOLS,
    ChannelProtocol,
)
from kubex.core.params import AttachOptions, NamespaceTypes
from kubex.core.request_builder.builder import RequestBuilder
from kubex_core.models.interfaces import HasAttach
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

__all__ = [
    "AttachAccessor",
    "_AttachDescriptor",
]

_A = TypeVar("_A", bound=HasAttach)


class AttachAccessor(Generic[ResourceType]):
    """Accessor for the Pod ``attach`` subresource.

    .. warning::

       **Experimental.** The WebSocket-based subresources (``exec``,
       ``attach``, ``portforward``) are still under active development and
       their API may change in future releases without notice.
    """

    def __init__(
        self,
        client: BaseClient,
        request_builder: RequestBuilder,
        namespace: NamespaceTypes,
        scope: Scope,
        resource_type: Type[ResourceType],
        *,
        channel_protocols: tuple[ChannelProtocol, ...] = DEFAULT_PROTOCOLS,
    ) -> None:
        self._client = client
        self._request_builder = request_builder
        self._namespace = namespace
        self._scope = scope
        self._resource_type = resource_type
        self._channel_protocols = channel_protocols

    async def _open_session(
        self,
        name: str,
        *,
        container: str | None,
        namespace: ApiNamespaceTypes,
        stdin: bool,
        stdout: bool,
        stderr: bool,
        tty: bool,
        request_timeout: ApiRequestTimeoutTypes,
    ) -> StreamSession:
        _namespace = ensure_required_namespace(namespace, self._namespace, self._scope)
        options = AttachOptions(
            container=container,
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            tty=tty,
        )
        request = self._request_builder.attach_request(
            name, _namespace, options, request_timeout=request_timeout
        )
        subprotocols = [p.subprotocol for p in self._channel_protocols]
        connection = await self._client.connect_websocket(
            request, subprotocols=subprotocols
        )
        try:
            protocol = _resolve_protocol(connection, self._channel_protocols)
            return StreamSession(
                connection,
                protocol,
                stdin=stdin,
                stdout=stdout,
                stderr=stderr,
                tty=tty,
            )
        except BaseException:
            try:
                await connection.close()
            except Exception:
                pass
            raise

    @asynccontextmanager
    async def stream(
        self,
        name: str,
        *,
        container: str | None = None,
        namespace: ApiNamespaceTypes = Ellipsis,
        stdin: bool = False,
        stdout: bool = True,
        stderr: bool = True,
        tty: bool = False,
        request_timeout: ApiRequestTimeoutTypes = Ellipsis,
    ) -> AsyncIterator[StreamSession]:
        """Open a bidirectional attach session as an async context manager.

        .. warning::

           **Experimental.** This WebSocket-based API is still under active
           development and may change in future releases without notice.
        """
        session = await self._open_session(
            name,
            container=container,
            namespace=namespace,
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            tty=tty,
            request_timeout=request_timeout,
        )
        async with session:
            yield session


class _AttachDescriptor(CachedSubresourceDescriptor):
    _marker = HasAttach
    _accessor_cls = AttachAccessor
    _error_message = "Attach is only supported for resources with HasAttach marker"

    @overload
    def __get__(self, instance: None, owner: type) -> _AttachDescriptor: ...

    @overload
    def __get__(self, instance: ApiProtocol[_A], owner: type) -> AttachAccessor[_A]: ...

    @overload
    def __get__(
        self, instance: ApiProtocol[Any], owner: type
    ) -> SubresourceNotAvailable: ...

    def __get__(self, instance: Any, owner: type | None = None) -> Any:
        return self._resolve(instance)
