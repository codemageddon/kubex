from __future__ import annotations

import anyio
import pytest

from kubex.api._portforward_session import PortForwardSession
from kubex.client.websocket import WebSocketConnection
from kubex.core.exceptions import KubexClientException
from kubex.core.exec_channels import (
    CHANNEL_CLOSE,
    V5ChannelProtocol,
    error_channel_for_port_index,
    port_prefix_encode,
)


@pytest.fixture(params=["asyncio", "trio"])
def anyio_backend(request: pytest.FixtureRequest) -> str:
    return str(request.param)


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


# Helpers for building portforward frames
def _data_frame(channel: int, payload: bytes) -> bytes:
    return bytes([channel]) + payload


def _close_frame(target_channel: int) -> bytes:
    return bytes([CHANNEL_CLOSE, target_channel])


@pytest.mark.anyio
async def test_opening_with_two_ports_exposes_streams_and_errors_for_each() -> None:
    fake = _FakeWebSocket()
    fake.feed_eof()

    async with PortForwardSession(
        fake, V5ChannelProtocol(), ports=[8080, 9090]
    ) as session:
        assert 8080 in session._streams_recv
        assert 9090 in session._streams_recv
        assert 8080 in session._errors_recv
        assert 9090 in session._errors_recv


@pytest.mark.anyio
async def test_data_channel_first_frame_port_prefix_consumed() -> None:
    fake = _FakeWebSocket()
    # data channel 0 = port index 0 = port 8080
    fake.feed(_data_frame(0, port_prefix_encode(8080) + b"hello"))
    fake.feed_eof()

    async with PortForwardSession(fake, V5ChannelProtocol(), ports=[8080]) as session:
        chunks = [c async for c in session._streams_recv[8080]]

    assert chunks == [b"hello"]


@pytest.mark.anyio
async def test_error_channel_first_frame_port_prefix_consumed() -> None:
    fake = _FakeWebSocket()
    # error channel 1 = port index 0 = port 8080
    fake.feed(_data_frame(1, port_prefix_encode(8080) + b"error text"))
    fake.feed_eof()

    async with PortForwardSession(fake, V5ChannelProtocol(), ports=[8080]) as session:
        errors = [e async for e in session._errors_recv[8080]]

    assert errors == ["error text"]


@pytest.mark.anyio
async def test_subsequent_data_frames_routed_without_prefix() -> None:
    fake = _FakeWebSocket()
    fake.feed(_data_frame(0, port_prefix_encode(8080) + b"first"))
    fake.feed(_data_frame(0, b"second"))
    fake.feed(_data_frame(0, b"third"))
    fake.feed_eof()

    async with PortForwardSession(fake, V5ChannelProtocol(), ports=[8080]) as session:
        chunks = [c async for c in session._streams_recv[8080]]

    assert chunks == [b"first", b"second", b"third"]


@pytest.mark.anyio
async def test_subsequent_error_frames_routed_without_prefix() -> None:
    fake = _FakeWebSocket()
    fake.feed(_data_frame(1, port_prefix_encode(8080) + b"first-error"))
    fake.feed(_data_frame(1, b"second-error"))
    fake.feed_eof()

    async with PortForwardSession(fake, V5ChannelProtocol(), ports=[8080]) as session:
        errors = [e async for e in session._errors_recv[8080]]

    assert errors == ["first-error", "second-error"]


@pytest.mark.anyio
async def test_two_ports_routing_independent() -> None:
    fake = _FakeWebSocket()
    # data channel 0 = port 8080, data channel 2 = port 9090
    fake.feed(_data_frame(0, port_prefix_encode(8080) + b"from-8080"))
    fake.feed(_data_frame(2, port_prefix_encode(9090) + b"from-9090"))
    fake.feed_eof()

    async with PortForwardSession(
        fake, V5ChannelProtocol(), ports=[8080, 9090]
    ) as session:
        chunks_8080 = [c async for c in session._streams_recv[8080]]
        chunks_9090 = [c async for c in session._streams_recv[9090]]

    assert chunks_8080 == [b"from-8080"]
    assert chunks_9090 == [b"from-9090"]


@pytest.mark.anyio
async def test_data_channel_port_mismatch_closes_session_with_exception() -> None:
    fake = _FakeWebSocket()
    # data channel 0 should carry 8080 prefix but we send 9090
    fake.feed(_data_frame(0, port_prefix_encode(9090) + b"data"))
    fake.feed_eof()

    with anyio.fail_after(2.0):
        with pytest.raises(KubexClientException):
            async with PortForwardSession(fake, V5ChannelProtocol(), ports=[8080]):
                # The read loop's exception cancels this body and is re-raised
                # on exit.
                await anyio.sleep_forever()


@pytest.mark.anyio
async def test_error_channel_port_mismatch_closes_session_with_exception() -> None:
    fake = _FakeWebSocket()
    # error channel 1 should carry 8080 prefix but we send 9090
    fake.feed(_data_frame(1, port_prefix_encode(9090) + b"err"))
    fake.feed_eof()

    with anyio.fail_after(2.0):
        with pytest.raises(KubexClientException):
            async with PortForwardSession(fake, V5ChannelProtocol(), ports=[8080]):
                await anyio.sleep_forever()


@pytest.mark.anyio
async def test_slow_data_consumer_receives_every_frame() -> None:
    """Regression: a full per-port queue used to close the port's stream and
    drop the rest of the data. The read loop now waits for the consumer."""
    frames = 300
    fake = _FakeWebSocket(buffer=frames + 8)
    fake.feed(_data_frame(0, port_prefix_encode(8080)))
    for i in range(frames):
        fake.feed(_data_frame(0, b"%04d" % i))
    fake.feed_eof()

    with anyio.fail_after(10.0):
        async with PortForwardSession(
            fake, V5ChannelProtocol(), ports=[8080], buffer_size=1
        ) as session:
            received = bytearray()
            async for chunk in session._streams_recv[8080]:
                received.extend(chunk)
                await anyio.sleep(0)

    assert received == b"".join(b"%04d" % i for i in range(frames))


@pytest.mark.anyio
async def test_slow_error_consumer_receives_every_error() -> None:
    fake = _FakeWebSocket()
    error_channel = error_channel_for_port_index(0)
    fake.feed(_data_frame(error_channel, port_prefix_encode(8080) + b"err0"))
    for i in range(1, 10):
        fake.feed(_data_frame(error_channel, b"err%d" % i))
    fake.feed_eof()

    with anyio.fail_after(5.0):
        async with PortForwardSession(
            fake, V5ChannelProtocol(), ports=[8080], buffer_size=1
        ) as session:
            errors = [e async for e in session._errors_recv[8080]]

    assert errors == [f"err{i}" for i in range(10)]


@pytest.mark.anyio
async def test_unread_port_stalls_other_ports_until_closed() -> None:
    """All ports share one WebSocket, so a port nobody reads holds back the
    others once its queue is full (kubectl behaves the same). Closing the
    unread stream releases the rest."""
    fake = _FakeWebSocket()
    fake.feed(_data_frame(0, port_prefix_encode(8080) + b"a1"))
    fake.feed(_data_frame(0, b"a2"))
    fake.feed(_data_frame(0, b"a3"))
    fake.feed(_data_frame(2, port_prefix_encode(9090) + b"b1"))

    async with PortForwardSession(
        fake, V5ChannelProtocol(), ports=[8080, 9090], buffer_size=1
    ) as session:
        with anyio.move_on_after(0.1) as scope:
            await session._streams[9090].receive()
        assert scope.cancelled_caught

        await session._streams[8080].aclose()
        with anyio.fail_after(2.0):
            assert await session._streams[9090].receive() == b"b1"


@pytest.mark.anyio
async def test_blocking_read_loop_unblocks_on_session_exit_when_buffer_full() -> None:
    fake = _FakeWebSocket(buffer=2048)
    # After the first data payload fills the buffer the read loop blocks
    # awaiting the consumer. Session teardown must cancel the blocked send
    # cleanly without deadlocking.
    fake.feed(_data_frame(0, port_prefix_encode(8080) + b"data"))
    fake.feed(_data_frame(0, b"second"))  # read loop blocks here (buffer full)

    with anyio.fail_after(2.0):
        async with PortForwardSession(
            fake, V5ChannelProtocol(), ports=[8080], buffer_size=1
        ):
            await anyio.sleep(0.05)

    assert fake.closed is True


@pytest.mark.anyio
async def test_context_manager_exit_does_not_deadlock_when_server_holds_connection() -> (
    None
):
    fake = _FakeWebSocket()
    # No feed_eof — server keeps connection open

    with anyio.fail_after(2.0):
        async with PortForwardSession(fake, V5ChannelProtocol(), ports=[8080]):
            pass

    assert fake.closed is True


@pytest.mark.anyio
async def test_close_port_data_emits_correct_close_frame() -> None:
    fake = _FakeWebSocket()
    fake.feed_eof()

    async with PortForwardSession(
        fake, V5ChannelProtocol(), ports=[8080, 9090]
    ) as session:
        await session.close_port_data(8080)

    # port 8080 is index 0, data channel = 0; CHANNEL_CLOSE frame = bytes([255, 0])
    assert fake.sent == [bytes([CHANNEL_CLOSE, 0])]


@pytest.mark.anyio
async def test_close_port_data_for_second_port_emits_correct_frame() -> None:
    fake = _FakeWebSocket()
    fake.feed_eof()

    async with PortForwardSession(
        fake, V5ChannelProtocol(), ports=[8080, 9090]
    ) as session:
        await session.close_port_data(9090)

    # port 9090 is index 1, data channel = 2; CHANNEL_CLOSE frame = bytes([255, 2])
    assert fake.sent == [bytes([CHANNEL_CLOSE, 2])]


@pytest.mark.anyio
async def test_close_port_data_is_idempotent() -> None:
    fake = _FakeWebSocket()
    fake.feed_eof()

    async with PortForwardSession(fake, V5ChannelProtocol(), ports=[8080]) as session:
        await session.close_port_data(8080)
        await session.close_port_data(8080)

    assert fake.sent == [bytes([CHANNEL_CLOSE, 0])]


@pytest.mark.anyio
async def test_inbound_channel_close_closes_data_receive_stream() -> None:
    fake = _FakeWebSocket()
    # First frame with port prefix, then CHANNEL_CLOSE targeting data channel 0
    fake.feed(_data_frame(0, port_prefix_encode(8080) + b"data"))
    fake.feed(_close_frame(0))
    fake.feed_eof()

    async with PortForwardSession(fake, V5ChannelProtocol(), ports=[8080]) as session:
        chunks = [c async for c in session._streams_recv[8080]]

    assert chunks == [b"data"]


@pytest.mark.anyio
async def test_inbound_channel_close_closes_error_receive_stream() -> None:
    fake = _FakeWebSocket()
    # First frame on error channel with port prefix, then CHANNEL_CLOSE targeting error channel 1
    fake.feed(_data_frame(1, port_prefix_encode(8080) + b"err"))
    fake.feed(_close_frame(1))
    fake.feed_eof()

    async with PortForwardSession(fake, V5ChannelProtocol(), ports=[8080]) as session:
        errors = [e async for e in session._errors_recv[8080]]

    assert errors == ["err"]


@pytest.mark.anyio
async def test_inbound_close_for_data_channel_does_not_affect_error_channel() -> None:
    fake = _FakeWebSocket()
    fake.feed(_data_frame(0, port_prefix_encode(8080) + b"data"))
    fake.feed(_close_frame(0))  # close data channel 0
    fake.feed(_data_frame(1, port_prefix_encode(8080) + b"err"))
    fake.feed(_close_frame(1))  # close error channel 1
    fake.feed_eof()

    async with PortForwardSession(fake, V5ChannelProtocol(), ports=[8080]) as session:
        chunks = [c async for c in session._streams_recv[8080]]
        errors = [e async for e in session._errors_recv[8080]]

    assert chunks == [b"data"]
    assert errors == ["err"]


@pytest.mark.anyio
async def test_first_frame_with_only_port_prefix_delivers_no_data() -> None:
    fake = _FakeWebSocket()
    # First frame is just the port prefix (empty body after stripping)
    fake.feed(_data_frame(0, port_prefix_encode(8080)))
    fake.feed(_data_frame(0, b"actual data"))
    fake.feed_eof()

    async with PortForwardSession(fake, V5ChannelProtocol(), ports=[8080]) as session:
        chunks = [c async for c in session._streams_recv[8080]]

    assert chunks == [b"actual data"]


@pytest.mark.anyio
async def test_data_frames_after_inbound_close_are_silently_discarded() -> None:
    fake = _FakeWebSocket()
    fake.feed(_data_frame(0, port_prefix_encode(8080) + b"before"))
    fake.feed(_close_frame(0))
    fake.feed(_data_frame(0, b"after"))  # should be discarded
    fake.feed_eof()

    async with PortForwardSession(fake, V5ChannelProtocol(), ports=[8080]) as session:
        chunks = [c async for c in session._streams_recv[8080]]

    assert chunks == [b"before"]


@pytest.mark.anyio
async def test_error_frames_after_inbound_close_are_silently_discarded() -> None:
    fake = _FakeWebSocket()
    fake.feed(_data_frame(1, port_prefix_encode(8080) + b"first-error"))
    fake.feed(_close_frame(1))
    fake.feed(_data_frame(1, b"second-error"))  # should be discarded
    fake.feed_eof()

    async with PortForwardSession(fake, V5ChannelProtocol(), ports=[8080]) as session:
        errors = [e async for e in session._errors_recv[8080]]

    assert errors == ["first-error"]


@pytest.mark.anyio
async def test_channel_close_with_empty_payload_does_not_close_any_stream() -> None:
    fake = _FakeWebSocket()
    # CHANNEL_CLOSE frame with no channel-id byte in the payload
    fake.feed(bytes([CHANNEL_CLOSE]))  # empty payload
    fake.feed(_data_frame(0, port_prefix_encode(8080) + b"data"))
    fake.feed_eof()

    async with PortForwardSession(fake, V5ChannelProtocol(), ports=[8080]) as session:
        chunks = [c async for c in session._streams_recv[8080]]

    assert chunks == [b"data"]


@pytest.mark.anyio
async def test_unknown_channel_id_is_silently_discarded() -> None:
    fake = _FakeWebSocket()
    # Channel 100 is not data (0) or error (1) for port 8080, so it is discarded.
    fake.feed(bytes([100]) + b"garbage")
    fake.feed(_data_frame(0, port_prefix_encode(8080) + b"valid"))
    fake.feed_eof()

    async with PortForwardSession(fake, V5ChannelProtocol(), ports=[8080]) as session:
        chunks = [c async for c in session._streams_recv[8080]]

    assert chunks == [b"valid"]


@pytest.mark.anyio
async def test_data_dispatch_consumer_closed_does_not_raise() -> None:
    """BrokenResourceError/ClosedResourceError from a closed consumer is swallowed."""
    fake = _FakeWebSocket()
    fake.feed(_data_frame(0, port_prefix_encode(8080) + b"data"))
    fake.feed(_data_frame(0, b"more"))
    fake.feed_eof()

    with anyio.fail_after(2.0):
        async with PortForwardSession(
            fake, V5ChannelProtocol(), ports=[8080]
        ) as session:
            # Close the receive end before the read loop dispatches frames.
            session._streams_recv[8080].close()
            await anyio.sleep(0)
            await anyio.sleep(0)


@pytest.mark.anyio
async def test_error_frame_with_invalid_utf8_uses_replacement_character() -> None:
    fake = _FakeWebSocket()
    # Port prefix + invalid UTF-8 bytes
    fake.feed(_data_frame(1, port_prefix_encode(8080) + b"\xff\xfe"))
    fake.feed_eof()

    async with PortForwardSession(fake, V5ChannelProtocol(), ports=[8080]) as session:
        errors = [e async for e in session._errors_recv[8080]]

    assert len(errors) == 1
    assert "\ufffd" in errors[0]
