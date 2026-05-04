from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

import anyio
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

from kubex.api._stream_session import _BaseChannelSession
from kubex.client.websocket import WebSocketConnection
from kubex.core.exceptions import KubexClientException
from kubex.core.exec_channels import (
    CHANNEL_CLOSE,
    ChannelProtocol,
    data_channel_for_port_index,
    error_channel_for_port_index,
    port_prefix_decode,
)

if TYPE_CHECKING:
    from kubex.api._portforward import PortForwardStream

__all__ = ["PortForwardSession"]

_DEFAULT_BUFFER: float = 128


class PortForwardSession(_BaseChannelSession):
    """Port-aware WebSocket channel multiplexer for the Kubernetes portforward subresource.

    Inherits lifecycle management (write lock, exit stack, task group) from
    ``_BaseChannelSession``.  Each port gets a data ``MemoryObjectStream[bytes]``
    and an error ``MemoryObjectStream[str]``.  The first frame on each channel
    carries a 2-byte little-endian port-number prefix which is stripped and
    validated; subsequent frames are routed as raw bytes (data) or UTF-8 text
    (error) without any prefix.

    When ``block_on_full=True`` the read loop awaits space in each per-port
    buffer instead of closing the stream on overflow.  This propagates
    backpressure all the way to the WebSocket — correct for single-port TCP
    proxy sessions created by ``listen()`` where data loss is unacceptable.
    When ``block_on_full=False`` (the default) the read loop uses a non-blocking
    send: if a port's buffer is full the port stream is closed locally and
    ``_truncated[port]`` is set, leaving all other ports unaffected.  This
    prevents head-of-line blocking across ports in multi-port ``forward()``
    sessions at the cost of surfacing overflow as ``EndOfStream`` rather than
    stalling traffic.
    """

    def __init__(
        self,
        connection: WebSocketConnection,
        protocol: ChannelProtocol,
        ports: Sequence[int],
        *,
        buffer_size: float = _DEFAULT_BUFFER,
        block_on_full: bool = False,
    ) -> None:
        super().__init__(connection, protocol)
        self._ports: tuple[int, ...] = tuple(ports)
        self._block_on_full = block_on_full

        # Channel-id → port lookup tables (built once, queried in _read_loop)
        self._data_ch_to_port: dict[int, int] = {}
        self._error_ch_to_port: dict[int, int] = {}

        # Per-port memory streams (keyed by port number)
        self._streams_send: dict[int, MemoryObjectSendStream[bytes]] = {}
        self._streams_recv: dict[int, MemoryObjectReceiveStream[bytes]] = {}
        self._errors_send: dict[int, MemoryObjectSendStream[str]] = {}
        self._errors_recv: dict[int, MemoryObjectReceiveStream[str]] = {}

        # Per-port PortForwardStream objects exposing the anyio.abc.ByteStream API.
        self._streams: dict[int, PortForwardStream] = {}

        # Overflow flags: set when a per-port data buffer fills and is closed locally.
        self._truncated: dict[int, bool] = {}

        # Whether each port's data / error channel is still accepting inbound frames.
        self._data_open: dict[int, bool] = {}
        self._error_open: dict[int, bool] = {}

        # Channels whose first frame (port prefix) has already been consumed.
        self._data_first_seen: set[int] = set()
        self._error_first_seen: set[int] = set()

        from kubex.api._portforward import PortForwardStream as _PortForwardStream

        for i, port in enumerate(self._ports):
            dc = data_channel_for_port_index(i)
            ec = error_channel_for_port_index(i)
            self._data_ch_to_port[dc] = port
            self._error_ch_to_port[ec] = port

            send_d, recv_d = anyio.create_memory_object_stream[bytes](
                max_buffer_size=buffer_size
            )
            send_e, recv_e = anyio.create_memory_object_stream[str](
                max_buffer_size=buffer_size
            )
            self._streams_send[port] = send_d
            self._streams_recv[port] = recv_d
            self._errors_send[port] = send_e
            self._errors_recv[port] = recv_e
            self._streams[port] = _PortForwardStream(self, port, dc, recv_d)
            self._truncated[port] = False
            self._data_open[port] = True
            self._error_open[port] = True

    def _before_cancel(self) -> None:
        for port in self._ports:
            self._streams_recv[port].close()
            self._errors_recv[port].close()

    async def close_port_data(self, port: int) -> None:
        """Send a half-close frame for the data channel of ``port``.

        Idempotent: a second call for the same port is a no-op.
        The emitted frame is ``protocol.encode(CHANNEL_CLOSE, bytes([data_channel_id]))``.
        """
        if port not in self._ports:
            raise ValueError(
                f"port {port} is not part of this portforward session (ports={list(self._ports)})"
            )
        port_index = self._ports.index(port)
        dc = data_channel_for_port_index(port_index)
        await self._send_close_for_channel(dc)

    async def _read_loop(self) -> None:
        try:
            while True:
                try:
                    frame = await self._connection.receive_bytes()
                except StopAsyncIteration:
                    break
                if not frame:
                    continue
                channel, payload = self._protocol.decode(frame)

                if channel == CHANNEL_CLOSE:
                    # Payload is 1 byte identifying the target channel being closed.
                    if payload:
                        self._handle_inbound_close(payload[0])

                elif channel in self._data_ch_to_port:
                    port = self._data_ch_to_port[channel]
                    if not self._data_open[port]:
                        continue
                    # First frame: validate the 2-byte port prefix.
                    if channel not in self._data_first_seen:
                        decoded_port = port_prefix_decode(payload)
                        if decoded_port != port:
                            raise KubexClientException(
                                f"portforward data channel {channel} carries port "
                                f"{decoded_port} but expected {port}"
                            )
                        self._data_first_seen.add(channel)
                        payload = payload[2:]
                    if payload:
                        if self._block_on_full:
                            still_open = await _dispatch_bytes(
                                self._streams_send[port], payload
                            )
                            self._data_open[port] = still_open
                        else:
                            still_open, truncated = _dispatch_bytes_nowait(
                                self._streams_send[port], payload
                            )
                            self._data_open[port] = still_open
                            if truncated:
                                self._truncated[port] = True

                elif channel in self._error_ch_to_port:
                    port = self._error_ch_to_port[channel]
                    if not self._error_open[port]:
                        continue
                    # First frame: validate the 2-byte port prefix.
                    if channel not in self._error_first_seen:
                        decoded_port = port_prefix_decode(payload)
                        if decoded_port != port:
                            raise KubexClientException(
                                f"portforward error channel {channel} carries port "
                                f"{decoded_port} but expected {port}"
                            )
                        self._error_first_seen.add(channel)
                        payload = payload[2:]
                    if payload:
                        error_text = payload.decode("utf-8", errors="replace")
                        if self._block_on_full:
                            still_open = await _dispatch_str(
                                self._errors_send[port], error_text
                            )
                            self._error_open[port] = still_open
                        else:
                            still_open, _ = _dispatch_str_nowait(
                                self._errors_send[port], error_text
                            )
                            self._error_open[port] = still_open
        finally:
            for port in self._ports:
                self._streams_send[port].close()
                self._errors_send[port].close()

    def _handle_inbound_close(self, target_channel: int) -> None:
        if target_channel in self._data_ch_to_port:
            port = self._data_ch_to_port[target_channel]
            self._streams_send[port].close()
            self._data_open[port] = False
        elif target_channel in self._error_ch_to_port:
            port = self._error_ch_to_port[target_channel]
            self._errors_send[port].close()
            self._error_open[port] = False


def _dispatch_bytes_nowait(
    send_stream: MemoryObjectSendStream[bytes], payload: bytes
) -> tuple[bool, bool]:
    """Push ``payload`` to ``send_stream`` without blocking.

    Returns ``(still_open, truncated)``.  ``still_open`` is ``False`` when the
    channel is closed; ``truncated`` is ``True`` only when *this* call closed
    the channel due to a full buffer.  Using ``send_nowait`` here means the
    read loop never stalls on a single port's consumer, so a slow consumer on
    port A cannot block frame delivery to port B (no head-of-line blocking).
    """
    try:
        send_stream.send_nowait(payload)
        return True, False
    except anyio.WouldBlock:
        send_stream.close()
        return False, True
    except (anyio.BrokenResourceError, anyio.ClosedResourceError):
        return False, False


def _dispatch_str_nowait(
    send_stream: MemoryObjectSendStream[str], text: str
) -> tuple[bool, bool]:
    """Push ``text`` to ``send_stream`` without blocking.

    Returns ``(still_open, truncated)``.
    """
    try:
        send_stream.send_nowait(text)
        return True, False
    except anyio.WouldBlock:
        send_stream.close()
        return False, True
    except (anyio.BrokenResourceError, anyio.ClosedResourceError):
        return False, False


async def _dispatch_bytes(
    send_stream: MemoryObjectSendStream[bytes], payload: bytes
) -> bool:
    """Push ``payload`` to ``send_stream``, blocking until space is available.

    Returns ``True`` if the send succeeded, ``False`` if the stream is closed.
    Blocking naturally propagates backpressure from a slow consumer through the
    memory buffer to the WebSocket read loop, preventing data loss.  Only used
    when ``block_on_full=True`` (the ``listen()`` TCP-proxy path).
    """
    try:
        await send_stream.send(payload)
        return True
    except (anyio.BrokenResourceError, anyio.ClosedResourceError):
        return False


async def _dispatch_str(send_stream: MemoryObjectSendStream[str], text: str) -> bool:
    """Push ``text`` to ``send_stream``, blocking until space is available.

    Returns ``True`` if the send succeeded, ``False`` if the stream is closed.
    """
    try:
        await send_stream.send(text)
        return True
    except (anyio.BrokenResourceError, anyio.ClosedResourceError):
        return False
