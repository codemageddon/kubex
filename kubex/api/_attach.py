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

        Output is never dropped: a channel whose consumer falls behind pauses
        the whole session (backpressure). Drain every enabled output channel
        concurrently, or disable the ones you don't need (e.g.
        ``stderr=False``).

        Attaches to the container's existing main process; no new command is
        started. Leaving the ``async with`` block closes the session.

        Args:
            name: The name of the Pod to attach to.
            container: The container to attach to. Required when the Pod has more
                than one container.
            namespace: The namespace of the Pod. If not provided,
                the namespace provided when creating the API will be used.
                The namespace is required for namespaced resources.
                If namespace is provided for cluster-scoped resources, an error will be raised.
            stdin: Attach to the process's stdin, for writing with ``session.stdin``.
            stdout: Attach to the process's stdout.
            stderr: Attach to the process's stderr. Ignored with ``tty=True``.
            tty: Attach as a terminal. The kubelet then merges stderr into stdout,
                so ``session.stderr`` closes immediately.
            request_timeout: HTTP-level timeout override for the WebSocket
                handshake. A number is interpreted as the total timeout in
                seconds. Pass ``None`` to disable timeouts entirely. Omit to use
                the client default. It does not bound the session itself.

        Yields:
            StreamSession: the open session, with ``stdin``, ``stdout``,
                ``stderr``, ``resize()``, ``close_stdin()`` and
                ``wait_for_status()``.

        Raises:
            ValueError: an argument is invalid, e.g. an empty or malformed ``name``,
                or a namespace that is missing for a namespace-scoped resource or
                given for a cluster-scoped one.
            KubexApiError: the WebSocket handshake was rejected; the subclass matches
                the HTTP status (e.g. ``NotFound`` for a missing pod, ``BadRequest``
                for an unknown container, ``Forbidden``).
            KubexConnectionError: the API server could not be reached.
            KubexTimeoutError: the WebSocket handshake timed out.
            KubexClientException: the WebSocket handshake failed for another reason,
                or the connection closed abnormally.
            ConfigurationError: credentials could not be obtained, or the httpx
                client is used without the ``httpx-ws`` extra installed.
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
