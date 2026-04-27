from __future__ import annotations

import anyio
import pytest

from kubex.api._stream_session import StreamSession
from kubex.client.websocket import WebSocketConnection
from kubex.core.exec_channels import V5ChannelProtocol


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class _FakeWebSocket(WebSocketConnection):
    """In-memory WebSocketConnection that feeds pre-staged frames to the read loop."""

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


@pytest.mark.anyio
async def test_stdout_yields_payload_from_channel_one() -> None:
    fake = _FakeWebSocket()
    fake.feed(bytes([1]) + b"hello")
    fake.feed_eof()

    async with StreamSession(fake, V5ChannelProtocol()) as session:
        chunks = [chunk async for chunk in session.stdout]

    assert chunks == [b"hello"]


@pytest.mark.anyio
async def test_stderr_yields_payload_from_channel_two() -> None:
    fake = _FakeWebSocket()
    fake.feed(bytes([2]) + b"err")
    fake.feed_eof()

    async with StreamSession(fake, V5ChannelProtocol()) as session:
        chunks = [chunk async for chunk in session.stderr]

    assert chunks == [b"err"]


@pytest.mark.anyio
async def test_dispatches_frames_to_correct_channels() -> None:
    fake = _FakeWebSocket()
    fake.feed(bytes([1]) + b"hello")
    fake.feed(bytes([2]) + b"err")
    fake.feed(bytes([3]) + b'{"metadata":{},"status":"Success"}')
    fake.feed_eof()

    async with StreamSession(fake, V5ChannelProtocol()) as session:
        stdout = [c async for c in session.stdout]
        stderr = [c async for c in session.stderr]
        status = await session.wait_for_status()

    assert stdout == [b"hello"]
    assert stderr == [b"err"]
    assert status is not None
    assert status.status == "Success"


@pytest.mark.anyio
async def test_status_resolves_to_none_when_no_error_frame_received() -> None:
    fake = _FakeWebSocket()
    fake.feed(bytes([1]) + b"only-stdout")
    fake.feed_eof()

    async with StreamSession(fake, V5ChannelProtocol()) as session:
        async for _ in session.stdout:
            pass
        status = await session.wait_for_status()

    assert status is None


@pytest.mark.anyio
async def test_unknown_inbound_channels_are_ignored() -> None:
    fake = _FakeWebSocket()
    fake.feed(bytes([99]) + b"junk")
    fake.feed(bytes([1]) + b"good")
    fake.feed_eof()

    async with StreamSession(fake, V5ChannelProtocol()) as session:
        chunks = [c async for c in session.stdout]

    assert chunks == [b"good"]


@pytest.mark.anyio
async def test_stdin_write_sends_channel_zero_frame() -> None:
    fake = _FakeWebSocket()
    fake.feed_eof()

    async with StreamSession(fake, V5ChannelProtocol(), stdin=True) as session:
        await session.stdin.write(b"input")

    assert fake.sent == [b"\x00input"]


@pytest.mark.anyio
async def test_stdin_writer_close_method_sends_v5_close_frame() -> None:
    fake = _FakeWebSocket()
    fake.feed_eof()

    async with StreamSession(fake, V5ChannelProtocol(), stdin=True) as session:
        await session.stdin.close()

    assert fake.sent == [b"\xff\x00"]


@pytest.mark.anyio
async def test_resize_sends_channel_four_frame_with_compact_json_payload() -> None:
    fake = _FakeWebSocket()
    fake.feed_eof()

    async with StreamSession(fake, V5ChannelProtocol()) as session:
        await session.resize(width=80, height=24)

    assert fake.sent == [b'\x04{"Width":80,"Height":24}']


@pytest.mark.anyio
async def test_close_stdin_sends_v5_close_frame_for_stdin_channel() -> None:
    fake = _FakeWebSocket()
    fake.feed_eof()

    async with StreamSession(fake, V5ChannelProtocol(), stdin=True) as session:
        await session.close_stdin()

    assert fake.sent == [b"\xff\x00"]


@pytest.mark.anyio
async def test_context_manager_closes_underlying_connection_on_exit() -> None:
    fake = _FakeWebSocket()
    fake.feed_eof()

    async with StreamSession(fake, V5ChannelProtocol()):
        pass

    assert fake.closed is True


@pytest.mark.anyio
async def test_exception_inside_block_still_closes_underlying_connection() -> None:
    fake = _FakeWebSocket()

    with pytest.raises(RuntimeError, match="boom"):
        async with StreamSession(fake, V5ChannelProtocol()):
            raise RuntimeError("boom")

    assert fake.closed is True


@pytest.mark.anyio
async def test_resize_during_iteration_does_not_corrupt_output() -> None:
    fake = _FakeWebSocket()
    fake.feed(bytes([1]) + b"first")
    fake.feed(bytes([1]) + b"second")
    fake.feed_eof()

    async with StreamSession(fake, V5ChannelProtocol()) as session:
        chunks: list[bytes] = []
        async for chunk in session.stdout:
            chunks.append(chunk)
            if len(chunks) == 1:
                await session.resize(width=100, height=40)

    assert chunks == [b"first", b"second"]
    assert b'\x04{"Width":100,"Height":40}' in fake.sent


@pytest.mark.anyio
async def test_clean_exit_without_eof_does_not_deadlock() -> None:
    """Regression: exiting the context manager while the server still holds the
    WebSocket open (no EOF) must not deadlock on the task-group join."""
    fake = _FakeWebSocket()
    # Note: NO feed_eof() — simulates a server that has not closed the channel.

    with anyio.fail_after(2.0):
        async with StreamSession(fake, V5ChannelProtocol(), stdin=True) as session:
            await session.stdin.write(b"hello")

    assert fake.closed is True


@pytest.mark.anyio
async def test_close_stdin_is_idempotent() -> None:
    fake = _FakeWebSocket()
    fake.feed_eof()

    async with StreamSession(fake, V5ChannelProtocol(), stdin=True) as session:
        await session.close_stdin()
        await session.close_stdin()
        await session.stdin.close()

    assert fake.sent == [b"\xff\x00"]


@pytest.mark.anyio
async def test_resize_rejects_non_positive_dimensions() -> None:
    fake = _FakeWebSocket()
    fake.feed_eof()

    async with StreamSession(fake, V5ChannelProtocol()) as session:
        with pytest.raises(ValueError, match="positive width and height"):
            await session.resize(width=0, height=24)
        with pytest.raises(ValueError, match="positive width and height"):
            await session.resize(width=80, height=-1)


@pytest.mark.anyio
async def test_stdin_write_after_close_raises() -> None:
    fake = _FakeWebSocket()
    fake.feed_eof()

    async with StreamSession(fake, V5ChannelProtocol(), stdin=True) as session:
        await session.close_stdin()
        with pytest.raises(RuntimeError, match="stdin is closed"):
            await session.stdin.write(b"too late")

    assert fake.sent == [b"\xff\x00"]


@pytest.mark.anyio
async def test_close_stdin_rolls_back_flag_on_send_failure() -> None:
    """If the close-frame send fails, ``_stdin_closed`` must be reset so a
    retry can actually deliver the close frame."""

    class _FailingThenOkWebSocket(_FakeWebSocket):
        def __init__(self) -> None:
            super().__init__()
            self._fail_next_send = True

        async def send_bytes(self, data: bytes) -> None:
            if self._fail_next_send:
                self._fail_next_send = False
                raise RuntimeError("transient send failure")
            await super().send_bytes(data)

    fake = _FailingThenOkWebSocket()
    fake.feed_eof()

    async with StreamSession(fake, V5ChannelProtocol(), stdin=True) as session:
        with pytest.raises(RuntimeError, match="transient send failure"):
            await session.close_stdin()
        # Retry succeeds; the close frame is actually delivered this time.
        await session.close_stdin()

    assert fake.sent == [b"\xff\x00"]


@pytest.mark.anyio
async def test_invalid_status_payload_does_not_crash_read_loop() -> None:
    fake = _FakeWebSocket()
    fake.feed(bytes([3]) + b"not valid json")
    fake.feed(bytes([1]) + b"after-error")
    fake.feed_eof()

    async with StreamSession(fake, V5ChannelProtocol()) as session:
        stdout = [c async for c in session.stdout]
        status = await session.wait_for_status()

    assert stdout == [b"after-error"]
    assert status is None


@pytest.mark.anyio
async def test_status_observable_when_consumer_does_not_drain_stdout() -> None:
    """Regression: a consumer that never reads stdout must not block error/EOF
    delivery. Earlier the bounded 128-frame buffer would deadlock the read
    loop once filled, starving channel 3 (status) and EOF detection."""
    fake = _FakeWebSocket(buffer=512)
    # Push more frames than the per-channel buffer would admit to make the
    # regression unambiguous, then a status frame, then EOF.
    for _ in range(200):
        fake.feed(bytes([1]) + b"chunk")
    fake.feed(bytes([3]) + b'{"metadata":{},"status":"Success"}')
    fake.feed_eof()

    with anyio.fail_after(2.0):
        async with StreamSession(fake, V5ChannelProtocol()) as session:
            # Deliberately do NOT iterate session.stdout. Status must still
            # arrive because the read loop cannot be parked on a full buffer.
            status = await session.wait_for_status()

    assert status is not None
    assert status.status == "Success"


@pytest.mark.anyio
async def test_stdout_buffer_overflow_closes_channel_without_oom() -> None:
    """Regression: a remote producer that floods one enabled channel while the
    consumer falls behind must not grow client memory unboundedly. When the
    bounded per-channel buffer fills, the read loop closes that channel
    locally (consumer observes EOF after draining what was buffered) instead
    of either blocking the wire (deadlock) or buffering forever (OOM).
    Sibling channels keep flowing."""
    fake = _FakeWebSocket(buffer=2048)
    # Feed far more than the per-channel buffer can hold.
    for _ in range(1000):
        fake.feed(bytes([1]) + b"flood")
    # Stderr arrives interleaved — must still be deliverable in full
    # because it has its own buffer and is being drained promptly below.
    fake.feed(bytes([2]) + b"err-1")
    fake.feed(bytes([2]) + b"err-2")
    fake.feed(bytes([3]) + b'{"metadata":{},"status":"Success"}')
    fake.feed_eof()

    with anyio.fail_after(2.0):
        async with StreamSession(fake, V5ChannelProtocol()) as session:
            stderr = [chunk async for chunk in session.stderr]
            status = await session.wait_for_status()
            # The stdout channel was closed locally on overflow; iterating
            # yields whatever was buffered up to the cap, then ends.
            stdout = [chunk async for chunk in session.stdout]

    assert stderr == [b"err-1", b"err-2"]
    assert status is not None and status.status == "Success"
    # Strictly bounded: never the full 1000 floods.
    assert len(stdout) <= 256
    assert all(chunk == b"flood" for chunk in stdout)
    # Consumer can observe that the EOF was a local truncation, not a
    # normal command end.
    assert session.stdout_truncated is True
    assert session.stderr_truncated is False


@pytest.mark.anyio
async def test_truncation_flags_false_on_clean_exit() -> None:
    """A normal command end (consumer keeps up, no overflow) must leave
    both ``*_truncated`` flags ``False`` so callers can rely on them as a
    truthy "we lost data" signal."""
    fake = _FakeWebSocket()
    fake.feed(bytes([1]) + b"out")
    fake.feed(bytes([2]) + b"err")
    fake.feed(bytes([3]) + b'{"metadata":{},"status":"Success"}')
    fake.feed_eof()

    async with StreamSession(fake, V5ChannelProtocol()) as session:
        [chunk async for chunk in session.stdout]
        [chunk async for chunk in session.stderr]
        await session.wait_for_status()

    assert session.stdout_truncated is False
    assert session.stderr_truncated is False


@pytest.mark.anyio
async def test_closed_stdout_does_not_silence_stderr_or_status() -> None:
    """Regression: dropping one channel's receive end used to ``break`` the
    whole read loop, killing all sibling channels with it."""
    fake = _FakeWebSocket()
    fake.feed(bytes([1]) + b"out")
    fake.feed(bytes([2]) + b"err")
    fake.feed(bytes([3]) + b'{"metadata":{},"status":"Success"}')
    fake.feed_eof()

    async with StreamSession(fake, V5ChannelProtocol()) as session:
        # Close stdout receive immediately; future stdout sends should fail
        # silently inside the read loop without affecting stderr/status.
        session.stdout.close()
        stderr = [c async for c in session.stderr]
        status = await session.wait_for_status()

    assert stderr == [b"err"]
    assert status is not None
    assert status.status == "Success"


@pytest.mark.anyio
async def test_write_queued_behind_close_observes_closed_state() -> None:
    """Regression: the flag check used to live *outside* the write lock, so
    a write queued behind a close (sharing the same lock) could see a stale
    ``_stdin_closed`` snapshot taken before the close ran. After the fix the
    check happens under the lock — once close releases the lock with the flag
    set, the queued write must observe it and raise instead of emitting a
    stdin data frame on the wire after the half-close.
    """

    class _SlowFirstSendWebSocket(_FakeWebSocket):
        """Holds the *first* send-under-lock until ``gate`` is set, giving the
        test a deterministic window to queue another sender behind the lock.
        """

        def __init__(self) -> None:
            super().__init__()
            self.gate = anyio.Event()
            self.first_send_started = anyio.Event()
            self._first_call = True

        async def send_bytes(self, data: bytes) -> None:
            self.sent.append(data)
            if self._first_call:
                self._first_call = False
                self.first_send_started.set()
                await self.gate.wait()

    fake = _SlowFirstSendWebSocket()
    fake.feed_eof()

    write_error: list[BaseException] = []

    async with StreamSession(fake, V5ChannelProtocol(), stdin=True) as session:

        async def _do_close() -> None:
            await session.close_stdin()

        async def _do_write() -> None:
            try:
                await session.stdin.write(b"data")
            except BaseException as exc:
                write_error.append(exc)

        async with anyio.create_task_group() as tg:
            tg.start_soon(_do_close)
            # Wait until close has acquired the lock and started its send
            # (now blocked in send_bytes on the gate).
            await fake.first_send_started.wait()
            tg.start_soon(_do_write)
            # Yield enough times for the write task to reach the lock-acquire
            # await and queue behind the close.
            for _ in range(10):
                await anyio.sleep(0)
            # Releasing the gate lets close finish its send and release the
            # lock; write then acquires, observes the flag set under the lock,
            # and raises — without emitting a stdin data frame on the wire.
            fake.gate.set()

    assert fake.sent == [b"\xff\x00"]
    assert len(write_error) == 1
    assert isinstance(write_error[0], RuntimeError)
    assert "stdin is closed" in str(write_error[0])


@pytest.mark.anyio
async def test_stderr_closes_immediately_when_tty_true() -> None:
    """When ``tty=True`` the kubelet merges stderr into stdout and never
    opens the stderr channel; iterating ``session.stderr`` must end at
    once instead of blocking until socket teardown."""
    fake = _FakeWebSocket()
    # No EOF — simulates a server keeping the WebSocket open. Iteration
    # over stderr must still terminate because the channel is closed locally.
    with anyio.fail_after(2.0):
        async with StreamSession(fake, V5ChannelProtocol(), tty=True) as session:
            chunks = [chunk async for chunk in session.stderr]

    assert chunks == []


@pytest.mark.anyio
async def test_stderr_closes_immediately_when_stderr_disabled() -> None:
    fake = _FakeWebSocket()
    with anyio.fail_after(2.0):
        async with StreamSession(fake, V5ChannelProtocol(), stderr=False) as session:
            chunks = [chunk async for chunk in session.stderr]

    assert chunks == []


@pytest.mark.anyio
async def test_stdout_closes_immediately_when_stdout_disabled() -> None:
    fake = _FakeWebSocket()
    with anyio.fail_after(2.0):
        async with StreamSession(fake, V5ChannelProtocol(), stdout=False) as session:
            chunks = [chunk async for chunk in session.stdout]

    assert chunks == []


@pytest.mark.anyio
async def test_stdin_write_raises_when_stdin_not_enabled() -> None:
    fake = _FakeWebSocket()
    fake.feed_eof()

    async with StreamSession(fake, V5ChannelProtocol()) as session:
        with pytest.raises(RuntimeError, match="stdin was not enabled"):
            await session.stdin.write(b"nope")

    assert fake.sent == []


@pytest.mark.anyio
async def test_close_stdin_is_noop_when_stdin_not_enabled() -> None:
    """``stdin=False`` means the channel was never opened; ``close_stdin``
    must not emit a CLOSE frame for a non-existent channel."""
    fake = _FakeWebSocket()
    fake.feed_eof()

    async with StreamSession(fake, V5ChannelProtocol()) as session:
        await session.close_stdin()
        await session.stdin.close()

    assert fake.sent == []


@pytest.mark.anyio
async def test_disabled_channels_ignore_unexpected_inbound_frames() -> None:
    """If a misbehaving server still pushes to a disabled channel the
    read loop must drop the frames instead of resurrecting the stream
    and surprising consumers that already saw EOF."""
    fake = _FakeWebSocket()
    fake.feed(bytes([1]) + b"unexpected-stdout")
    fake.feed(bytes([2]) + b"unexpected-stderr")
    fake.feed_eof()

    async with StreamSession(
        fake, V5ChannelProtocol(), stdout=False, stderr=False
    ) as session:
        stdout = [c async for c in session.stdout]
        stderr = [c async for c in session.stderr]

    assert stdout == []
    assert stderr == []
