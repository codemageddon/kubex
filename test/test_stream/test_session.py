from __future__ import annotations

import json

import anyio
import pytest

from kubex.api._stream_session import _MAX_FRAME_PAYLOAD, StreamSession
from kubex.client.websocket import WebSocketConnection
from kubex.core.exceptions import KubexClientException
from kubex.core.exec_channels import V5ChannelProtocol

_SUCCESS = b'{"metadata":{},"status":"Success"}'


def _exit_status(code: int) -> bytes:
    return json.dumps(
        {
            "metadata": {},
            "status": "Failure",
            "reason": "NonZeroExitCode",
            "message": f"command terminated with exit code {code}",
            "details": {"causes": [{"reason": "ExitCode", "message": str(code)}]},
        }
    ).encode()


@pytest.fixture(params=["asyncio", "trio"])
def anyio_backend(request: pytest.FixtureRequest) -> str:
    return str(request.param)


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
async def test_non_json_status_payload_becomes_failure_status() -> None:
    """A garbled error channel must not crash the read loop, and must not be
    reported as "no status": it surfaces as a Failure carrying the text."""
    fake = _FakeWebSocket()
    fake.feed(bytes([3]) + b"not valid json")
    fake.feed(bytes([1]) + b"after-error")
    fake.feed_eof()

    async with StreamSession(fake, V5ChannelProtocol()) as session:
        stdout = [c async for c in session.stdout]
        status = await session.wait_for_status()

    assert stdout == [b"after-error"]
    assert status is not None
    assert status.status == "Failure"
    assert status.message == "not valid json"


@pytest.mark.anyio
async def test_empty_error_frame_does_not_resolve_status() -> None:
    """Regression: the server's empty "connection established" frame lands on
    the error channel when stdout/stderr are disabled. It used to resolve
    ``wait_for_status()`` immediately with ``None``."""
    fake = _FakeWebSocket()
    fake.feed(bytes([3]))

    async with StreamSession(
        fake, V5ChannelProtocol(), stdout=False, stderr=False
    ) as session:
        with anyio.move_on_after(0.1) as scope:
            await session.wait_for_status()
        assert scope.cancelled_caught

        fake.feed(bytes([3]) + _exit_status(3))
        with anyio.fail_after(2.0):
            status = await session.wait_for_status()

    assert status is not None
    assert status.details is not None and status.details.causes is not None
    assert status.details.causes[0].message == "3"


@pytest.mark.anyio
async def test_status_split_across_frames_is_reassembled() -> None:
    payload = _exit_status(42)
    fake = _FakeWebSocket()
    fake.feed(bytes([3]) + payload[:10])
    fake.feed(bytes([3]) + payload[10:25])
    fake.feed(bytes([3]) + payload[25:])

    async with StreamSession(fake, V5ChannelProtocol(), stdout=False) as session:
        with anyio.fail_after(2.0):
            status = await session.wait_for_status()

    assert status is not None and status.reason == "NonZeroExitCode"


@pytest.mark.anyio
async def test_status_without_metadata_is_parsed() -> None:
    fake = _FakeWebSocket()
    fake.feed(bytes([3]) + b'{"status":"Success"}')
    fake.feed_eof()

    async with StreamSession(fake, V5ChannelProtocol()) as session:
        status = await session.wait_for_status()

    assert status is not None and status.status == "Success"


@pytest.mark.anyio
async def test_incomplete_status_at_eof_becomes_failure_status() -> None:
    fake = _FakeWebSocket()
    fake.feed(bytes([3]) + b'{"status":"Fail')
    fake.feed_eof()

    async with StreamSession(fake, V5ChannelProtocol()) as session:
        status = await session.wait_for_status()

    assert status is not None
    assert status.status == "Failure"
    assert status.message == '{"status":"Fail'


@pytest.mark.anyio
async def test_empty_payloads_are_not_delivered_to_consumers() -> None:
    fake = _FakeWebSocket()
    fake.feed(bytes([1]))
    fake.feed(bytes([2]))
    fake.feed(bytes([1]) + b"out")
    fake.feed(bytes([2]) + b"err")
    fake.feed(bytes([1]))
    fake.feed_eof()

    async with StreamSession(fake, V5ChannelProtocol()) as session:
        stdout = [c async for c in session.stdout]
        stderr = [c async for c in session.stderr]

    assert stdout == [b"out"]
    assert stderr == [b"err"]


@pytest.mark.anyio
async def test_slow_consumer_receives_every_frame() -> None:
    """Regression: a full per-channel queue used to close the channel and
    drop the rest of the output while the process kept running. The read
    loop now waits for the consumer instead."""
    frames = 1000
    fake = _FakeWebSocket(buffer=frames + 8)
    for i in range(frames):
        fake.feed(bytes([1]) + b"line %04d\n" % i)
    fake.feed(bytes([3]) + _SUCCESS)
    fake.feed_eof()

    received = bytearray()
    with anyio.fail_after(10.0):
        async with StreamSession(
            fake, V5ChannelProtocol(), stderr=False, buffer_size=2
        ) as session:
            async for chunk in session.stdout:
                received.extend(chunk)
                await anyio.sleep(0)
            status = await session.wait_for_status()

    assert received == b"".join(b"line %04d\n" % i for i in range(frames))
    assert status is not None and status.status == "Success"


@pytest.mark.anyio
async def test_status_waits_behind_undrained_output() -> None:
    """Backpressure is in-order: the status frame is only read once earlier
    output has been consumed. Draining stdout releases it."""
    fake = _FakeWebSocket()
    for _ in range(5):
        fake.feed(bytes([1]) + b"chunk")
    fake.feed(bytes([3]) + _SUCCESS)
    fake.feed_eof()

    async with StreamSession(fake, V5ChannelProtocol(), buffer_size=1) as session:
        with anyio.move_on_after(0.1) as scope:
            await session.wait_for_status()
        assert scope.cancelled_caught
        chunks = [c async for c in session.stdout]
        with anyio.fail_after(2.0):
            status = await session.wait_for_status()

    assert chunks == [b"chunk"] * 5
    assert status is not None and status.status == "Success"


@pytest.mark.anyio
async def test_closing_a_receive_stream_discards_that_channel() -> None:
    """Closing ``session.stderr`` is the opt-out for a channel the caller
    does not want: its frames are dropped and the rest keeps flowing."""
    fake = _FakeWebSocket()
    for _ in range(50):
        fake.feed(bytes([2]) + b"noise")
    fake.feed(bytes([1]) + b"wanted")
    fake.feed(bytes([3]) + _SUCCESS)
    fake.feed_eof()

    with anyio.fail_after(2.0):
        async with StreamSession(fake, V5ChannelProtocol(), buffer_size=2) as session:
            session.stderr.close()
            stdout = [c async for c in session.stdout]
            status = await session.wait_for_status()

    assert stdout == [b"wanted"]
    assert status is not None and status.status == "Success"


@pytest.mark.anyio
async def test_exit_does_not_deadlock_when_stderr_floods_and_only_stdout_is_read() -> (
    None
):
    """A consumer reading only stdout while the process floods stderr stalls
    (stderr's queue is full, so later stdout frames are never read) — that
    is the documented cost of backpressure. Leaving the context manager must
    still tear the session down promptly."""
    fake = _FakeWebSocket(buffer=512)
    for _ in range(200):
        fake.feed(bytes([2]) + b"err")
    fake.feed(bytes([1]) + b"done")
    # No EOF: the server keeps the connection open.

    stdout: list[bytes] = []
    with anyio.fail_after(2.0):
        async with StreamSession(fake, V5ChannelProtocol(), buffer_size=4) as session:
            with anyio.move_on_after(0.2):
                async for chunk in session.stdout:
                    stdout.append(chunk)

    assert stdout == []
    assert fake.closed is True


@pytest.mark.anyio
async def test_outer_cancel_while_read_loop_is_blocked_tears_down_promptly() -> None:
    fake = _FakeWebSocket(buffer=512)
    for _ in range(100):
        fake.feed(bytes([1]) + b"x")

    with anyio.fail_after(2.0):
        with anyio.move_on_after(0.1) as scope:
            async with StreamSession(fake, V5ChannelProtocol(), buffer_size=1):
                await anyio.sleep_forever()

    assert scope.cancelled_caught
    assert fake.closed is True


def _stdin_frames(sent: list[bytes]) -> list[bytes]:
    return [frame for frame in sent if frame[0] == 0]


@pytest.mark.anyio
async def test_large_stdin_write_is_split_into_32k_frames() -> None:
    """Regression: a large write used to go out as one WebSocket message,
    which the API server drops (closing with 1000) above its size cap."""
    data = bytes(range(256)) * 400  # 100 KiB
    fake = _FakeWebSocket()

    async with StreamSession(fake, V5ChannelProtocol(), stdin=True) as session:
        await session.stdin.write(data)

    frames = _stdin_frames(fake.sent)
    assert len(frames) == 4
    assert all(len(frame) - 1 <= _MAX_FRAME_PAYLOAD for frame in frames)
    assert b"".join(frame[1:] for frame in frames) == data


@pytest.mark.anyio
async def test_stdin_writes_stay_contiguous_while_resize_interleaves() -> None:
    """Frames of one stdin write must not interleave with another stdin
    write, but a resize must not wait for a whole large write either."""

    class _GatedWebSocket(_FakeWebSocket):
        def __init__(self) -> None:
            super().__init__()
            self.first_send = anyio.Event()
            self.gate = anyio.Event()

        async def send_bytes(self, data: bytes) -> None:
            self.sent.append(data)
            if not self.first_send.is_set():
                self.first_send.set()
                await self.gate.wait()
            await anyio.sleep(0)

    chunk = _MAX_FRAME_PAYLOAD
    a = b"a" * (3 * chunk)
    b = b"b" * (2 * chunk)
    fake = _GatedWebSocket()

    async with StreamSession(fake, V5ChannelProtocol(), stdin=True) as session:
        async with anyio.create_task_group() as tg:
            tg.start_soon(session.stdin.write, a)
            await fake.first_send.wait()
            tg.start_soon(session.stdin.write, b)
            for _ in range(5):
                await anyio.sleep(0)
            tg.start_soon(lambda: session.resize(width=80, height=24))
            for _ in range(5):
                await anyio.sleep(0)
            fake.gate.set()

    kinds = [frame[:2] for frame in fake.sent]
    assert kinds == [
        b"\x00a",
        b"\x04{",
        b"\x00a",
        b"\x00a",
        b"\x00b",
        b"\x00b",
    ]


@pytest.mark.anyio
async def test_writes_after_session_exit_raise_kubex_client_exception() -> None:
    fake = _FakeWebSocket()
    fake.feed_eof()

    async with StreamSession(fake, V5ChannelProtocol(), stdin=True) as session:
        pass

    with pytest.raises(KubexClientException, match="closed"):
        await session.stdin.write(b"late")
    with pytest.raises(KubexClientException, match="closed"):
        await session.resize(width=80, height=24)
    with pytest.raises(KubexClientException, match="closed"):
        await session.close_stdin()
    assert fake.sent == []


@pytest.mark.anyio
async def test_close_stdin_after_exit_is_noop_when_already_closed() -> None:
    fake = _FakeWebSocket()
    fake.feed_eof()

    async with StreamSession(fake, V5ChannelProtocol(), stdin=True) as session:
        await session.close_stdin()

    await session.close_stdin()
    assert fake.sent == [b"\xff\x00"]


@pytest.mark.anyio
async def test_truncation_flags_are_deprecated_and_always_false() -> None:
    fake = _FakeWebSocket()
    fake.feed_eof()

    async with StreamSession(fake, V5ChannelProtocol()) as session:
        pass

    with pytest.warns(DeprecationWarning):
        assert session.stdout_truncated is False
    with pytest.warns(DeprecationWarning):
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
