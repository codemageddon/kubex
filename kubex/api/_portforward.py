from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from types import MappingProxyType
from typing import (
    Any,
    AsyncIterator,
    Generic,
    Mapping,
    Sequence,
    Type,
    TypeVar,
    overload,
)

import anyio
import anyio.abc
from anyio.streams.memory import MemoryObjectReceiveStream

from kubex.api._stream_session import _resolve_protocol
from kubex.api._portforward_session import PortForwardSession
from kubex.client.client import BaseClient
from kubex.core.exec_channels import (
    PORTFORWARD_PROTOCOLS,
    ChannelProtocol,
)
from kubex.core.params import NamespaceTypes, PortForwardOptions
from kubex.core.request_builder.builder import RequestBuilder
from kubex_core.models.interfaces import HasPortForward
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

_logger = logging.getLogger("kubex.portforward")


async def _copy(
    src: anyio.abc.ByteStream,
    dst: anyio.abc.ByteStream,
) -> None:
    """Copy bytes from src to dst until EOF, then half-close dst.

    On natural EOF on the source, sends EOF on the destination so the peer
    can keep streaming in the opposite direction (TCP half-close support).
    Errors propagate to the surrounding task group, which cancels the other
    copy task — full teardown happens via the outer ``async with`` blocks.
    """
    try:
        while True:
            try:
                chunk = await src.receive()
            except anyio.EndOfStream:
                break
            await dst.send(chunk)
    except (anyio.ClosedResourceError, anyio.BrokenResourceError):
        return
    try:
        await dst.send_eof()
    except (anyio.ClosedResourceError, anyio.BrokenResourceError):
        pass


async def _drain_errors(
    error_recv: MemoryObjectReceiveStream[str],
    port: int,
    cancel_scope: anyio.CancelScope | None = None,
) -> None:
    """Drain and log kubelet error messages for a port.

    If ``cancel_scope`` is provided, it is cancelled upon the first error frame so
    that the associated connection is torn down (matching kubectl port-forward semantics).
    """
    try:
        async for error_text in error_recv:
            _logger.warning("portforward error on port %d: %s", port, error_text)
            if cancel_scope is not None:
                cancel_scope.cancel()
                break
    except anyio.ClosedResourceError:
        pass


__all__ = [
    "PortForwardStream",
    "PortForwarder",
    "PortforwardAccessor",
    "_PortforwardDescriptor",
]

_P = TypeVar("_P", bound=HasPortForward)


class PortForwardStream(anyio.abc.ByteStream):
    """Per-port bidirectional byte stream for the Kubernetes portforward subresource.

    Wraps a ``PortForwardSession``'s data channel for a single port and implements
    ``anyio.abc.ByteStream`` so it integrates naturally with anyio byte-stream consumers.

    Outbound ``send()`` encodes the payload as a channel frame addressed to the
    port's data channel.  Inbound ``receive()`` reads from the session's per-port
    memory stream, buffering excess bytes to satisfy ``max_bytes`` slicing.

    ``aclose()`` half-closes the data channel (idempotent via the underlying
    session helper) and prevents further ``send()`` calls.  ``send_eof()``
    performs the same half-close without locking out receives.  On the v4
    portforward subprotocol — which the kubelet requires — half-close is a
    local-only state change; the kubelet ignores wire CHANNEL_CLOSE frames
    on v4 and tears down the channel only when the session WebSocket closes.
    """

    def __init__(
        self,
        session: PortForwardSession,
        port: int,
        data_channel_id: int,
        recv_stream: MemoryObjectReceiveStream[bytes],
    ) -> None:
        self._session = session
        self._port = port
        self._data_channel_id = data_channel_id
        self._recv_stream = recv_stream
        self._buffer = b""
        self._send_closed = False

    async def receive(self, max_bytes: int = 65536) -> bytes:
        if max_bytes <= 0:
            raise ValueError(f"max_bytes must be positive, got {max_bytes}")
        while not self._buffer:
            try:
                self._buffer = await self._recv_stream.receive()
            except (anyio.ClosedResourceError, anyio.EndOfStream):
                raise anyio.EndOfStream()
        data = self._buffer[:max_bytes]
        self._buffer = self._buffer[max_bytes:]
        return data

    async def send(self, item: bytes) -> None:
        # Acquire the session write lock *before* the closed-flag check so
        # check-then-send is atomic with respect to concurrent send_eof()
        # and aclose() callers (which set the flag under the same lock).
        # Without this, a writer that snapshotted the flag as ``False``
        # could still emit a data frame after the half-close had completed,
        # violating the half-close contract on protocols where it matters.
        async with self._session._write_lock:
            if self._send_closed:
                raise anyio.ClosedResourceError("stream send side is closed")
            await self._session._send_locked(self._data_channel_id, item)

    async def send_eof(self) -> None:
        async with self._session._write_lock:
            self._send_closed = True
        await self._session.close_port_data(self._port)

    async def aclose(self) -> None:
        async with self._session._write_lock:
            self._send_closed = True
        try:
            await self._session.close_port_data(self._port)
        finally:
            self._recv_stream.close()


class PortForwarder:
    """Holds an active portforward session and exposes per-port streams and errors.

    ``streams[port]`` is a ``PortForwardStream`` (``anyio.abc.ByteStream``) for
    sending and receiving raw bytes to/from the remote port.
    ``errors[port]`` is an async iterator of error-text strings sent by the kubelet
    on the error channel for that port.
    ``port_data_truncated[port]`` reflects the live overflow flag — ``True`` when the
    per-port data buffer filled and the stream was closed locally.
    """

    def __init__(self, session: PortForwardSession) -> None:
        self._session = session

    @property
    def streams(self) -> Mapping[int, PortForwardStream]:
        return MappingProxyType(self._session._streams)

    @property
    def errors(self) -> Mapping[int, MemoryObjectReceiveStream[str]]:
        return MappingProxyType(self._session._errors_recv)

    @property
    def port_data_truncated(self) -> Mapping[int, bool]:
        return MappingProxyType(self._session._truncated)


class PortforwardAccessor(Generic[ResourceType]):
    """Accessor for the Pod ``portforward`` subresource.

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
        channel_protocols: tuple[ChannelProtocol, ...] = PORTFORWARD_PROTOCOLS,
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
        ports: Sequence[int],
        namespace: ApiNamespaceTypes,
        request_timeout: ApiRequestTimeoutTypes,
        buffer_size: float = 128,
    ) -> PortForwardSession:
        _namespace = ensure_required_namespace(namespace, self._namespace, self._scope)
        options = PortForwardOptions(ports=ports)
        request = self._request_builder.portforward_request(
            name, _namespace, options, request_timeout=request_timeout
        )
        subprotocols = [p.subprotocol for p in self._channel_protocols]
        connection = await self._client.connect_websocket(
            request, subprotocols=subprotocols
        )
        try:
            protocol = _resolve_protocol(connection, self._channel_protocols)
            return PortForwardSession(
                connection, protocol, ports, buffer_size=buffer_size
            )
        except BaseException:
            try:
                await connection.close()
            except Exception:
                pass
            raise

    @asynccontextmanager
    async def forward(
        self,
        name: str,
        *,
        ports: Sequence[int],
        namespace: ApiNamespaceTypes = Ellipsis,
        request_timeout: ApiRequestTimeoutTypes = Ellipsis,
    ) -> AsyncIterator[PortForwarder]:
        """Open portforward streams to the given ports as an async context manager.

        .. warning::

           **Experimental.** This WebSocket-based API is still under active
           development and may change in future releases without notice.

        This is the **low-level** entry point: a single WebSocket multiplexes
        all requested ports, and the caller drives I/O directly in Python via
        per-port ``anyio.abc.ByteStream`` objects. No sockets are bound on the
        host — bytes never leave the process. Use this when your own code
        speaks to the pod (custom protocols, embedded clients, tests).

        For the kubectl-style mode where external processes connect through
        a real local TCP port, use :meth:`listen` instead (which is built on
        top of this method).

        Yields a ``PortForwarder`` exposing per-port ``ByteStream`` objects
        (``pf.streams[port]``) and per-port error iterators (``pf.errors[port]``).
        """
        session = await self._open_session(
            name,
            ports=ports,
            namespace=namespace,
            request_timeout=request_timeout,
        )
        async with session:
            yield PortForwarder(session)

    @asynccontextmanager
    async def listen(
        self,
        name: str,
        *,
        port_map: Mapping[int, int],
        local_host: str = "127.0.0.1",
        namespace: ApiNamespaceTypes = Ellipsis,
        request_timeout: ApiRequestTimeoutTypes = Ellipsis,
    ) -> AsyncIterator[None]:
        """Open local TCP listeners and forward bytes bidirectionally to remote ports.

        .. warning::

           **Experimental.** This WebSocket-based API is still under active
           development and may change in future releases without notice.

        This is the **high-level**, kubectl-style entry point: real OS sockets
        are bound on ``local_host:local_port`` so that any process on the host
        (``curl``, ``psql``, a browser, …) can connect to the pod through a
        local port. Each accepted local connection opens its own portforward
        WebSocket session bound to that single remote port — one session per
        connection, matching ``kubectl port-forward`` semantics. The method
        itself yields ``None``; you don't drive I/O through it.

        For the low-level mode where your own Python code reads/writes bytes
        directly without binding any sockets, use :meth:`forward` instead
        (which this method is built on top of).

        ``port_map`` maps **remote port** (kubelet-side) to **local port**.
        Example: ``{80: 18080}`` opens a local listener on port 18080 that
        forwards to the pod's port 80.
        """
        if not port_map:
            raise ValueError("port_map must contain at least one entry")
        # Validate ports up front so a config error fails at context entry
        # instead of being deferred to the first incoming connection where
        # it would surface as a swallowed log line. Booleans are rejected
        # explicitly because ``bool`` is an ``int`` subclass — without this,
        # ``port_map={80: False}`` would silently bind port 0 (ephemeral),
        # which the caller has no way to discover since ``listen()`` yields
        # ``None``.
        for remote_port, local_port in port_map.items():
            if isinstance(remote_port, bool) or not isinstance(remote_port, int):
                raise TypeError(
                    f"remote port must be int, got {type(remote_port).__name__}"
                )
            if not 1 <= remote_port <= 65535:
                raise ValueError(f"remote port {remote_port} out of range 1..65535")
            if isinstance(local_port, bool) or not isinstance(local_port, int):
                raise TypeError(
                    f"local port must be int, got {type(local_port).__name__}"
                )
            if not 1 <= local_port <= 65535:
                raise ValueError(f"local port {local_port} out of range 1..65535")
        local_ports = list(port_map.values())
        if len(set(local_ports)) != len(local_ports):
            raise ValueError(f"duplicate local ports in port_map: {local_ports}")
        async with anyio.create_task_group() as tg:
            for remote_port, local_port in port_map.items():
                await tg.start(
                    self._serve_port,
                    name,
                    remote_port,
                    local_port,
                    local_host,
                    namespace,
                    request_timeout,
                )
            try:
                yield
            finally:
                tg.cancel_scope.cancel()

    async def _serve_port(
        self,
        name: str,
        remote_port: int,
        local_port: int,
        local_host: str,
        namespace: ApiNamespaceTypes,
        request_timeout: ApiRequestTimeoutTypes,
        *,
        task_status: anyio.abc.TaskStatus[None] = anyio.TASK_STATUS_IGNORED,
    ) -> None:
        tcp_listener = await anyio.create_tcp_listener(
            local_host=local_host, local_port=local_port
        )
        async with tcp_listener:
            task_status.started(None)

            async def _handle(stream: anyio.abc.ByteStream) -> None:
                try:
                    async with stream:
                        session = await self._open_session(
                            name,
                            ports=[remote_port],
                            namespace=namespace,
                            request_timeout=request_timeout,
                        )
                        async with session:
                            pf = PortForwarder(session)
                            port_stream = pf.streams[remote_port]
                            error_recv = pf.errors[remote_port]
                            async with anyio.create_task_group() as conn_tg:
                                conn_tg.start_soon(
                                    _drain_errors,
                                    error_recv,
                                    remote_port,
                                    conn_tg.cancel_scope,
                                )
                                # Run the two copy directions in a nested task
                                # group so their natural EOFs (half-close) do
                                # not tear down the whole connection — only
                                # when both directions complete do we cancel
                                # the surrounding scope (which stops the error
                                # drain task).
                                async with anyio.create_task_group() as copy_tg:
                                    copy_tg.start_soon(_copy, stream, port_stream)
                                    copy_tg.start_soon(_copy, port_stream, stream)
                                conn_tg.cancel_scope.cancel()
                            if pf.port_data_truncated.get(remote_port):
                                _logger.warning(
                                    "portforward: data dropped for port %d due "
                                    "to local backpressure (buffer overflow); "
                                    "the local connection received truncated bytes",
                                    remote_port,
                                )
                except Exception:
                    _logger.exception(
                        "portforward connection error on port %d", remote_port
                    )

            await tcp_listener.serve(_handle)


class _PortforwardDescriptor(CachedSubresourceDescriptor):
    _marker = HasPortForward
    _accessor_cls = PortforwardAccessor
    _error_message = (
        "PortForward is only supported for resources with HasPortForward marker"
    )

    @overload
    def __get__(self, instance: None, owner: type) -> _PortforwardDescriptor: ...

    @overload
    def __get__(
        self, instance: ApiProtocol[_P], owner: type
    ) -> PortforwardAccessor[_P]: ...

    @overload
    def __get__(
        self, instance: ApiProtocol[Any], owner: type
    ) -> SubresourceNotAvailable: ...

    def __get__(self, instance: Any, owner: type | None = None) -> Any:
        return self._resolve(instance)
