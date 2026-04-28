from __future__ import annotations

import anyio
import pytest

from kubex.api._stream_session import _BaseChannelSession
from kubex.client.websocket import WebSocketConnection
from kubex.core.exec_channels import CHANNEL_CLOSE, ChannelProtocol, V5ChannelProtocol


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


class _SimpleSession(_BaseChannelSession):
    """Minimal concrete subclass for testing _BaseChannelSession lifecycle."""

    def __init__(
        self, connection: WebSocketConnection, protocol: ChannelProtocol
    ) -> None:
        super().__init__(connection, protocol)
        self.received: list[bytes] = []

    async def _read_loop(self) -> None:
        try:
            while True:
                try:
                    frame = await self._connection.receive_bytes()
                except StopAsyncIteration:
                    break
                if frame:
                    _, payload = self._protocol.decode(frame)
                    self.received.append(payload)
        finally:
            pass


@pytest.mark.anyio
async def test_lifo_close_order_connection_closes_after_read_loop() -> None:
    order: list[str] = []

    class _TrackingWebSocket(_FakeWebSocket):
        async def close(self) -> None:
            order.append("connection_closed")
            await super().close()

    class _TrackingSession(_SimpleSession):
        async def _read_loop(self) -> None:
            try:
                await super()._read_loop()
            finally:
                order.append("read_loop_done")

    fake = _TrackingWebSocket()
    fake.feed_eof()

    async with _TrackingSession(fake, V5ChannelProtocol()):
        pass

    assert order == ["read_loop_done", "connection_closed"]


@pytest.mark.anyio
async def test_clean_exit_without_eof_does_not_deadlock() -> None:
    fake = _FakeWebSocket()
    # No feed_eof() — simulates server holding connection open.

    with anyio.fail_after(2.0):
        async with _SimpleSession(fake, V5ChannelProtocol()):
            pass

    assert fake.closed is True


@pytest.mark.anyio
async def test_exception_inside_block_still_closes_connection() -> None:
    fake = _FakeWebSocket()

    with pytest.raises(RuntimeError, match="boom"):
        async with _SimpleSession(fake, V5ChannelProtocol()):
            raise RuntimeError("boom")

    assert fake.closed is True


@pytest.mark.anyio
async def test_write_lock_held_across_encode_and_send() -> None:
    """Two concurrent _send_frame calls must not interleave their bytes."""
    frames_sent: list[bytes] = []
    gate = anyio.Event()
    first_entered = anyio.Event()

    class _GatedWebSocket(_FakeWebSocket):
        _first = True

        async def send_bytes(self, data: bytes) -> None:
            frames_sent.append(data)
            if self._first:
                self._first = False
                first_entered.set()
                await gate.wait()

    fake = _GatedWebSocket()
    fake.feed_eof()

    async with _SimpleSession(fake, V5ChannelProtocol()) as session:
        async with anyio.create_task_group() as tg:
            tg.start_soon(session._send_frame, 0, b"first")
            await first_entered.wait()
            tg.start_soon(session._send_frame, 1, b"second")
            for _ in range(10):
                await anyio.sleep(0)
            gate.set()

    assert frames_sent == [b"\x00first", b"\x01second"]


@pytest.mark.anyio
async def test_send_close_for_channel_encoding() -> None:
    fake = _FakeWebSocket()
    fake.feed_eof()

    async with _SimpleSession(fake, V5ChannelProtocol()) as session:
        await session._send_close_for_channel(0)

    assert fake.sent == [bytes([CHANNEL_CLOSE, 0])]


@pytest.mark.anyio
async def test_send_close_for_channel_nonzero_target() -> None:
    fake = _FakeWebSocket()
    fake.feed_eof()

    async with _SimpleSession(fake, V5ChannelProtocol()) as session:
        await session._send_close_for_channel(3)

    assert fake.sent == [bytes([CHANNEL_CLOSE, 3])]


@pytest.mark.anyio
async def test_send_close_for_channel_is_idempotent() -> None:
    """Calling _send_close_for_channel twice for the same channel sends only one frame."""
    fake = _FakeWebSocket()
    fake.feed_eof()

    async with _SimpleSession(fake, V5ChannelProtocol()) as session:
        await session._send_close_for_channel(0)
        await session._send_close_for_channel(0)

    assert fake.sent == [bytes([CHANNEL_CLOSE, 0])]
