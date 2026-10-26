from __future__ import annotations

import logging
import warnings
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

from kubex.api._stream_session import _DEFAULT_CHANNEL_BUFFER, _resolve_protocol
from kubex.api._portforward_session import PortForwardSession
from kubex.client.client import BaseClient
from kubex.core.exceptions import KubexClientException
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


_COPY_ERRORS = (
    anyio.ClosedResourceError,
    anyio.BrokenResourceError,
    KubexClientException,
)


async def _copy(
    src: anyio.abc.ByteStream,
    dst: anyio.abc.ByteStream,
    *,
    direction: str,
    port: int,
) -> bool:
    """Copy bytes from src to dst until EOF, then half-close dst.

    Returns ``True`` when ``src`` reached EOF, ``False`` when the copy stopped
    on a closed/broken stream or a WebSocket error. Those are expected
    disconnects, so they are logged at debug level without a traceback.
    """
    try:
        while True:
            try:
                chunk = await src.receive()
            except anyio.EndOfStream:
                break
            await dst.send(chunk)
    except _COPY_ERRORS as exc:
        _logger.debug(
            "portforward %s copy on port %d stopped: %r", direction, port, exc
        )
        return False
    try:
        await dst.send_eof()
    except _COPY_ERRORS:
        pass
    return True


async def _copy_local_to_remote(
    local: anyio.abc.ByteStream,
    remote: anyio.abc.ByteStream,
    port: int,
    cancel_scope: anyio.CancelScope,
) -> None:
    # Local EOF is only a half-close: keep waiting for the remote response.
    # A local error tears the connection down (kubectl does the same).
    if not await _copy(local, remote, direction="local->remote", port=port):
        cancel_scope.cancel()


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


def _log_pending_errors(error_recv: MemoryObjectReceiveStream[str], port: int) -> None:
    """Log error messages already queued when the connection is torn down."""
    while True:
        try:
            error_text = error_recv.receive_nowait()
        except (anyio.WouldBlock, anyio.EndOfStream, anyio.ClosedResourceError):
            return
        _logger.warning("portforward error on port %d: %s", port, error_text)


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
        # Keeps the frames of one ``send()`` contiguous and orders them
        # against ``send_eof()`` / ``aclose()``.
        self._send_lock = anyio.Lock()

    async def receive(self, max_bytes: int = 65536) -> bytes:
        """Receive bytes from the remote port, waiting until some arrive.

        A frame larger than ``max_bytes`` is returned over several calls.

        Args:
            max_bytes: The maximum number of bytes to return.

        Returns:
            bytes: between 1 and ``max_bytes`` bytes received from the pod.

        Raises:
            ValueError: ``max_bytes`` is not positive.
            anyio.EndOfStream: no more data will arrive: the kubelet closed the
                port's data channel, the session ended, or this stream was closed
                with ``aclose()``.
        """
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
        """Send ``item`` to the remote port, split into frames of at most 32 KiB.

        Args:
            item: The bytes to send.

        Raises:
            anyio.ClosedResourceError: ``send_eof()`` or ``aclose()`` was called.
            KubexClientException: the session has already ended.
        """
        # The closed-flag check happens under the same lock that
        # send_eof()/aclose() take, so no data frame can follow a half-close.
        async with self._send_lock:
            if self._send_closed:
                raise anyio.ClosedResourceError("stream send side is closed")
            await self._session._send_data(self._data_channel_id, item)

    async def send_eof(self) -> None:
        """Close the sending side of the stream; ``receive()`` keeps working.

        Later ``send()`` calls raise ``anyio.ClosedResourceError``; calling this
        again is a no-op. On the v4 portforward protocol (the only one the
        kubelet supports) nothing is sent on the wire: the pod is not told about
        the EOF and only sees the connection end when the session's WebSocket
        closes.
        """
        async with self._send_lock:
            self._send_closed = True
        await self._session.close_port_data(self._port)

    async def aclose(self) -> None:
        """Close both directions of the stream.

        The sending side is closed as by ``send_eof()``. On the receiving side,
        ``receive()`` raises ``anyio.EndOfStream`` once any bytes left over from a
        partly read frame are returned, and data that arrives for this port
        afterwards is discarded, so an unread port no longer stalls the others.
        The session and its other ports stay open.
        """
        async with self._send_lock:
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

    All ports share one WebSocket and inbound data is never dropped: a port
    whose stream (or error iterator) is not read stalls every port once its
    queue is full. Read each forwarded port, or ``aclose()`` its stream.
    """

    def __init__(self, session: PortForwardSession) -> None:
        self._session = session

    @property
    def streams(self) -> Mapping[int, PortForwardStream]:
        """Per-port byte streams (``PortForwardStream``), keyed by remote port."""
        return MappingProxyType(self._session._streams)

    @property
    def errors(self) -> Mapping[int, MemoryObjectReceiveStream[str]]:
        """Per-port async iterators of kubelet error messages, keyed by remote port."""
        return MappingProxyType(self._session._errors_recv)

    @property
    def port_data_truncated(self) -> Mapping[int, bool]:
        """Deprecated: always ``False`` for every port (data is no longer dropped)."""
        return self._deprecated_truncated("port_data_truncated")

    @property
    def port_error_truncated(self) -> Mapping[int, bool]:
        """Deprecated: always ``False`` for every port (errors are no longer dropped)."""
        return self._deprecated_truncated("port_error_truncated")

    def _deprecated_truncated(self, name: str) -> Mapping[int, bool]:
        warnings.warn(
            f"PortForwarder.{name} is deprecated and always False: "
            "data is no longer dropped",
            DeprecationWarning,
            stacklevel=3,
        )
        return MappingProxyType(dict.fromkeys(self._session._ports, False))


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
        buffer_size: float = _DEFAULT_CHANNEL_BUFFER,
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

        Inbound data is never dropped; since the ports share one WebSocket, a
        port that is not read stalls all ports once its queue fills. Read
        every forwarded port (or ``aclose()`` the ones you don't need).

        Args:
            name: The name of the pod.
            ports: The pod ports to forward: 1 to 127 unique ports in 1..65535.
                Each becomes a key of ``streams`` and ``errors``.
            namespace: The namespace of the pod. If not provided,
                the namespace provided when creating the API will be used.
                The namespace is required for namespaced resources.
                If namespace is provided for cluster-scoped resources, an error will be raised.
            request_timeout: HTTP-level timeout override for the WebSocket
                handshake. A number is interpreted as the total timeout in
                seconds. Pass ``None`` to disable timeouts entirely. Omit to use
                the client default. It does not bound the session itself.

        Yields:
            PortForwarder: the per-port byte streams (``pf.streams[port]``) and
                error iterators (``pf.errors[port]``). The session's WebSocket is
                closed when the ``async with`` block exits.

        Raises:
            ValueError: an argument is invalid, e.g. an empty or malformed ``name``,
                or a namespace that is missing for a namespace-scoped resource or
                given for a cluster-scoped one; or ``ports`` is empty,
                has duplicates or more than 127 entries, or a port is outside
                1..65535.
            TypeError: a port is not an ``int``.
            KubexApiError: the WebSocket handshake was rejected; the subclass matches
                the HTTP status (e.g. ``NotFound`` for a missing pod, ``Forbidden``).
            KubexConnectionError: the API server could not be reached.
            KubexTimeoutError: the WebSocket handshake timed out.
            KubexClientException: the WebSocket handshake failed for another reason,
                or the connection closed abnormally.
            ConfigurationError: credentials could not be obtained, or the httpx
                client is used without the ``httpx-ws`` extra installed.
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

        When the remote side finishes (or the kubelet reports an error), the
        local connection is closed; a local half-close (EOF) keeps the
        connection open until the remote response is complete. The v4
        protocol cannot pass that EOF to the pod, so after a local client
        disconnects its connection stays open until the pod closes it or
        sends more data. Failures on individual connections (including a
        rejected WebSocket handshake) are logged to the ``kubex.portforward``
        logger rather than raised.

        Args:
            name: The name of the pod.
            port_map: Maps each **remote port** (on the pod) to the **local port**
                to listen on. Example: ``{80: 18080}`` opens a local listener on
                port 18080 that forwards to the pod's port 80.
            local_host: The local address the listeners bind to. The default,
                ``127.0.0.1``, only accepts connections from this host.
            namespace: The namespace of the pod. If not provided,
                the namespace provided when creating the API will be used.
                The namespace is required for namespaced resources.
                If namespace is provided for cluster-scoped resources, an error will be raised.
            request_timeout: HTTP-level timeout override for the WebSocket
                handshake of each accepted connection. A number is interpreted as
                the total timeout in seconds. Pass ``None`` to disable timeouts
                entirely. Omit to use the client default. It does not bound the
                connections themselves.

        Yields:
            None: the listeners stay open while the ``async with`` block runs;
                leaving it closes them and tears down open connections.

        Raises:
            ValueError: ``port_map`` is empty, a port is outside 1..65535, or two
                remote ports map to the same local port.
            TypeError: a port is not an ``int``.
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
                                conn_tg.start_soon(
                                    _copy_local_to_remote,
                                    stream,
                                    port_stream,
                                    remote_port,
                                    conn_tg.cancel_scope,
                                )
                                # Once the remote side is done, stop reading
                                # the local socket and close it (kubectl
                                # semantics) instead of leaving it half-open.
                                await _copy(
                                    port_stream,
                                    stream,
                                    direction="remote->local",
                                    port=remote_port,
                                )
                                conn_tg.cancel_scope.cancel()
                            _log_pending_errors(error_recv, remote_port)
                except KubexClientException as exc:
                    _logger.warning(
                        "portforward connection on port %d failed: %s",
                        remote_port,
                        exc,
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
