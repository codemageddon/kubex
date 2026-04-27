from __future__ import annotations

import anyio
import anyio.abc
import pytest

from kubex.api._portforward import PortForwardStream
from kubex.api._portforward_session import PortForwardSession
from kubex.client.websocket import WebSocketConnection
from kubex.core.exec_channels import (
    CHANNEL_CLOSE,
    V5ChannelProtocol,
    port_prefix_encode,
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class _FakeWebSocket(WebSocketConnection):
    def __init__(
        self,
        *,
        subprotocol: str | None = "v5.channel.k8s.io",
        buffer: int = 128,
    ) -> None:
        self.sent: list[bytes] = []
        self._send, self._recv = anyio.create_memory_object_stream[bytes](
            max_buffer_size=buffer
        )
        self._closed = False
        self._subprotocol = subprotocol

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def negotiated_subprotocol(self) -> str | None:
        return self._subprotocol

    async def send_bytes(self, data: bytes) -> None:
        self.sent.append(data)

    async def receive_bytes(self) -> bytes:
        try:
            return await self._recv.receive()
        except anyio.EndOfStream as exc:
            raise StopAsyncIteration from exc

    async def close(self) -> None:
        if not self._closed:
            self._closed = True
            self._send.close()

    def feed(self, frame: bytes) -> None:
        self._send.send_nowait(frame)

    def feed_eof(self) -> None:
        self._send.close()


def _data_frame(channel: int, payload: bytes) -> bytes:
    return bytes([channel]) + payload


@pytest.mark.anyio
async def test_send_emits_correct_v5_frame() -> None:
    fake = _FakeWebSocket()
    fake.feed_eof()

    async with PortForwardSession(fake, V5ChannelProtocol(), ports=[8080]) as session:
        stream = session._streams[8080]
        await stream.send(b"x")

    # data channel for port index 0 = channel 0; v5 frame = bytes([0]) + payload
    assert fake.sent == [bytes([0]) + b"x"]


@pytest.mark.anyio
async def test_receive_max_bytes_slices_frame() -> None:
    fake = _FakeWebSocket()
    fake.feed(_data_frame(0, port_prefix_encode(8080) + b"hello world"))
    fake.feed_eof()

    async with PortForwardSession(fake, V5ChannelProtocol(), ports=[8080]) as session:
        stream = session._streams[8080]
        first = await stream.receive(max_bytes=4)
        assert first == b"hell"
        rest = await stream.receive()
        assert rest == b"o world"


@pytest.mark.anyio
async def test_receive_no_arg_returns_full_buffered_chunk() -> None:
    fake = _FakeWebSocket()
    fake.feed(_data_frame(0, port_prefix_encode(8080) + b"abc"))
    fake.feed_eof()

    async with PortForwardSession(fake, V5ChannelProtocol(), ports=[8080]) as session:
        stream = session._streams[8080]
        data = await stream.receive()
        assert data == b"abc"


@pytest.mark.anyio
async def test_receive_eof_raises_end_of_stream() -> None:
    fake = _FakeWebSocket()
    # First frame carries only the port prefix (no body → nothing dispatched to queue)
    fake.feed(_data_frame(0, port_prefix_encode(8080)))
    # Server closes the data channel
    fake.feed(bytes([CHANNEL_CLOSE, 0]))
    fake.feed_eof()

    with pytest.raises(anyio.EndOfStream):
        async with PortForwardSession(
            fake, V5ChannelProtocol(), ports=[8080]
        ) as session:
            stream = session._streams[8080]
            await stream.receive()


@pytest.mark.anyio
async def test_aclose_emits_close_frame() -> None:
    fake = _FakeWebSocket()
    fake.feed_eof()

    async with PortForwardSession(fake, V5ChannelProtocol(), ports=[8080]) as session:
        stream = session._streams[8080]
        await stream.aclose()

    # CHANNEL_CLOSE (255) targeting data channel 0 → bytes([255, 0])
    assert fake.sent == [bytes([CHANNEL_CLOSE, 0])]


@pytest.mark.anyio
async def test_aclose_is_idempotent() -> None:
    fake = _FakeWebSocket()
    fake.feed_eof()

    async with PortForwardSession(fake, V5ChannelProtocol(), ports=[8080]) as session:
        stream = session._streams[8080]
        await stream.aclose()
        await stream.aclose()

    assert fake.sent == [bytes([CHANNEL_CLOSE, 0])]


@pytest.mark.anyio
async def test_send_after_aclose_raises_closed_resource_error() -> None:
    fake = _FakeWebSocket()
    fake.feed_eof()

    async with PortForwardSession(fake, V5ChannelProtocol(), ports=[8080]) as session:
        stream = session._streams[8080]
        await stream.aclose()
        with pytest.raises(anyio.ClosedResourceError):
            await stream.send(b"data")


@pytest.mark.anyio
async def test_is_anyio_bytestream_instance() -> None:
    fake = _FakeWebSocket()
    fake.feed_eof()

    async with PortForwardSession(fake, V5ChannelProtocol(), ports=[8080]) as session:
        stream = session._streams[8080]
        assert isinstance(stream, PortForwardStream)
        assert isinstance(stream, anyio.abc.ByteStream)


@pytest.mark.anyio
async def test_send_eof_emits_close_frame() -> None:
    fake = _FakeWebSocket()
    fake.feed_eof()

    async with PortForwardSession(fake, V5ChannelProtocol(), ports=[8080]) as session:
        stream = session._streams[8080]
        await stream.send_eof()

    assert fake.sent == [bytes([CHANNEL_CLOSE, 0])]


@pytest.mark.anyio
async def test_send_eof_prevents_further_sends() -> None:
    fake = _FakeWebSocket()
    fake.feed_eof()

    async with PortForwardSession(fake, V5ChannelProtocol(), ports=[8080]) as session:
        stream = session._streams[8080]
        await stream.send_eof()
        with pytest.raises(anyio.ClosedResourceError):
            await stream.send(b"data")


@pytest.mark.anyio
async def test_send_eof_is_idempotent() -> None:
    fake = _FakeWebSocket()
    fake.feed_eof()

    async with PortForwardSession(fake, V5ChannelProtocol(), ports=[8080]) as session:
        stream = session._streams[8080]
        await stream.send_eof()
        await stream.send_eof()

    assert fake.sent == [bytes([CHANNEL_CLOSE, 0])]
