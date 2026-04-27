from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

__all__ = [
    "CHANNEL_CLOSE",
    "CHANNEL_ERROR",
    "CHANNEL_RESIZE",
    "CHANNEL_STDERR",
    "CHANNEL_STDIN",
    "CHANNEL_STDOUT",
    "DEFAULT_PROTOCOLS",
    "PORTFORWARD_PROTOCOLS",
    "ChannelProtocol",
    "V4ChannelProtocol",
    "V5ChannelProtocol",
    "data_channel_for_port_index",
    "error_channel_for_port_index",
    "port_prefix_decode",
    "port_prefix_encode",
    "select_protocol",
]

CHANNEL_STDIN = 0
CHANNEL_STDOUT = 1
CHANNEL_STDERR = 2
CHANNEL_ERROR = 3
CHANNEL_RESIZE = 4
CHANNEL_CLOSE = 255


class ChannelProtocol(ABC):
    subprotocol: ClassVar[str]

    @abstractmethod
    def encode(self, channel: int, payload: bytes) -> bytes: ...

    @abstractmethod
    def decode(self, frame: bytes) -> tuple[int, bytes]: ...

    @abstractmethod
    def supports_close(self) -> bool: ...


class V5ChannelProtocol(ChannelProtocol):
    subprotocol: ClassVar[str] = "v5.channel.k8s.io"

    def encode(self, channel: int, payload: bytes) -> bytes:
        if not 0 <= channel <= 255:
            raise ValueError(f"channel id {channel} out of range [0, 255]")
        return bytes([channel]) + payload

    def decode(self, frame: bytes) -> tuple[int, bytes]:
        if len(frame) == 0:
            raise ValueError("cannot decode empty frame")
        return frame[0], frame[1:]

    def supports_close(self) -> bool:
        return True


class V4ChannelProtocol(ChannelProtocol):
    # The kubelet portforward WebSocket handler only registers v4
    # subprotocols; v5 (which adds CHANNEL_CLOSE) is rejected with 403.
    # See pkg/kubelet/cri/streaming/portforward/websocket.go.
    subprotocol: ClassVar[str] = "v4.channel.k8s.io"

    def encode(self, channel: int, payload: bytes) -> bytes:
        if not 0 <= channel <= 255:
            raise ValueError(f"channel id {channel} out of range [0, 255]")
        return bytes([channel]) + payload

    def decode(self, frame: bytes) -> tuple[int, bytes]:
        if len(frame) == 0:
            raise ValueError("cannot decode empty frame")
        return frame[0], frame[1:]

    def supports_close(self) -> bool:
        return False


DEFAULT_PROTOCOLS: tuple[ChannelProtocol, ...] = (V5ChannelProtocol(),)
PORTFORWARD_PROTOCOLS: tuple[ChannelProtocol, ...] = (V4ChannelProtocol(),)


def data_channel_for_port_index(index: int) -> int:
    return 2 * index


def error_channel_for_port_index(index: int) -> int:
    return 2 * index + 1


def port_prefix_encode(port: int) -> bytes:
    return port.to_bytes(2, byteorder="little")


def port_prefix_decode(data: bytes) -> int:
    from kubex.core.exceptions import KubexClientException

    if len(data) < 2:
        raise KubexClientException(
            f"port prefix requires at least 2 bytes, got {len(data)}"
        )
    return int.from_bytes(data[:2], byteorder="little")


def select_protocol(
    server_subprotocol: str | None,
    protocols: tuple[ChannelProtocol, ...] = DEFAULT_PROTOCOLS,
) -> ChannelProtocol:
    if server_subprotocol is None:
        raise ValueError("server did not negotiate a channel subprotocol")
    for protocol in protocols:
        if protocol.subprotocol == server_subprotocol:
            return protocol
    raise ValueError(
        f"server selected unsupported subprotocol {server_subprotocol!r}; "
        f"supported: {[p.subprotocol for p in protocols]}"
    )
