from __future__ import annotations

import json
import logging
import warnings
from abc import ABC, abstractmethod
from contextlib import AsyncExitStack
from types import TracebackType
from typing import Any, Iterator, Self, TypeVar

import anyio
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from kubex_core.models.status import Status
from pydantic import ValidationError

from kubex.client.websocket import WebSocketConnection
from kubex.core.exceptions import KubexClientException
from kubex.core.exec_channels import (
    CHANNEL_CLOSE,
    CHANNEL_ERROR,
    CHANNEL_RESIZE,
    CHANNEL_STDERR,
    CHANNEL_STDIN,
    CHANNEL_STDOUT,
    ChannelProtocol,
    select_protocol,
)

__all__ = ["StreamSession", "_BaseChannelSession", "_resolve_protocol"]

_logger = logging.getLogger("kubex.stream")


def _resolve_protocol(
    connection: WebSocketConnection, protocols: tuple[ChannelProtocol, ...]
) -> ChannelProtocol:
    # Both backend adapters already raise ``KubexClientException`` when the
    # server returns no subprotocol, but if a misbehaving server picks one
    # outside the requested list, ``select_protocol`` raises ``ValueError``.
    # Normalise to the documented exec/attach exception type.
    try:
        return select_protocol(connection.negotiated_subprotocol, protocols)
    except ValueError as exc:
        raise KubexClientException(str(exc)) from exc


# Per-channel queue depth (in frames) for inbound data. When a consumer falls
# behind and its queue fills, the read loop *waits* for it (blocking
# backpressure, like client-go's pipes): nothing is dropped, and the stall
# propagates through the WebSocket to the remote process. The flip side is
# that every enabled channel must be drained (or disabled / closed by the
# caller), otherwise the session stalls once that channel's queue is full.
_DEFAULT_CHANNEL_BUFFER = 128

# Largest payload sent in one outbound frame (client-go's io.Copy buffer).
# The API server drops WebSocket messages above its own size cap and closes
# with 1000, which would otherwise look like a clean EOF.
_MAX_FRAME_PAYLOAD = 32 * 1024

# Cap on buffered error-channel bytes; a Status document is a few KiB.
_MAX_ERROR_BYTES = 1 << 20

_T = TypeVar("_T")


def _iter_chunks(data: bytes) -> Iterator[bytes]:
    """Split ``data`` into ``_MAX_FRAME_PAYLOAD``-sized frames (at least one)."""
    if len(data) <= _MAX_FRAME_PAYLOAD:
        yield data
        return
    view = memoryview(data)
    for start in range(0, len(view), _MAX_FRAME_PAYLOAD):
        yield bytes(view[start : start + _MAX_FRAME_PAYLOAD])


async def _dispatch(send_stream: MemoryObjectSendStream[_T], item: _T) -> bool:
    """Push ``item`` to ``send_stream``, waiting for queue space if needed.

    Returns ``False`` once the consumer has closed its receive end (the
    channel is then discarded so sibling channels keep flowing). Session
    teardown closes every receive end first, so a read loop parked here is
    released immediately rather than deadlocking the task-group join.
    """
    try:
        await send_stream.send(item)
        return True
    except (anyio.BrokenResourceError, anyio.ClosedResourceError):
        return False


def _parse_status(raw: bytes | bytearray, doc: Any) -> Status:
    """Build a ``Status`` from an error-channel document, leniently.

    ``metadata`` is filled in when absent. Anything that still does not
    validate is surfaced as a ``Failure`` carrying the raw text, so callers
    are never told "no status" when the server did report an error.
    """
    if isinstance(doc, dict):
        if doc.get("metadata") is None:
            doc = {**doc, "metadata": {}}
        try:
            return Status.model_validate(doc)
        except ValidationError as exc:
            _logger.debug("error channel carried an invalid Status: %s", exc)
    text = bytes(raw).decode("utf-8", errors="replace").strip()
    return Status.model_validate({"metadata": {}, "status": "Failure", "message": text})


class _BaseChannelSession(ABC):
    """Shared lifecycle for Kubernetes channel-protocol WebSocket sessions.

    Owns the connection, write lock, exit stack, and background read-loop task.
    Subclasses provide ``_read_loop`` and may override ``_before_cancel`` to
    close per-channel receive streams before the task group is cancelled.
    """

    def __init__(
        self,
        connection: WebSocketConnection,
        protocol: ChannelProtocol,
    ) -> None:
        self._connection = connection
        self._protocol = protocol
        self._write_lock = anyio.Lock()
        self._exit_stack: AsyncExitStack | None = None
        self._task_group: anyio.abc.TaskGroup | None = None
        # True between a successful ``__aenter__`` and the start of
        # ``__aexit__``; writes outside that window raise
        # ``KubexClientException`` instead of a backend-specific error.
        self._open = False
        # Tracks channels for which a half-close frame has been sent so that
        # ``_send_close_for_channel`` is idempotent without requiring each
        # subclass to maintain its own flag per channel.
        self._closed_channels: set[int] = set()

    async def __aenter__(self) -> Self:
        stack = AsyncExitStack()
        await stack.__aenter__()
        try:
            # Order matters: the connection's underlying context manager
            # (e.g. ``httpx_ws.aconnect_ws``) holds an internal anyio task
            # group whose cancel scope was opened by ``connect_websocket``,
            # *before* this task group. anyio requires cancel scopes to
            # exit in LIFO order, so the connection close — which exits
            # that older scope — must run *after* this task group's
            # ``__aexit__`` has closed its own scope. The close is *not*
            # wrapped in an ``anyio.CancelScope(shield=True)``: shielding
            # would push a fresh scope onto this task between the cm's
            # internal scope and its ``__aexit__``, violating LIFO order
            # and crashing with "attempted to exit a cancel scope that
            # isn't the current task's current cancel scope". External
            # cancellation can therefore interrupt the close mid-flight;
            # ``run()`` mitigates this by keeping its own ``fail_after``
            # inside ``async with session`` so its scope exits before
            # teardown — callers wrapping ``run()`` in their own outer
            # cancel scope must accept the equivalent transport-leak risk.
            stack.push_async_callback(self._connection.close)
            tg = await stack.enter_async_context(anyio.create_task_group())
            tg.start_soon(self._read_loop)
            self._task_group = tg
        except BaseException:
            await stack.aclose()
            raise
        self._exit_stack = stack
        self._open = True
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        self._open = False
        stack = self._exit_stack
        self._exit_stack = None
        if stack is None:
            return None
        # Subclasses close their per-channel receive ends here so that a
        # read loop blocked on a full queue (backpressure) unblocks with
        # BrokenResourceError rather than deadlocking the task-group join.
        self._before_cancel()
        # Cancel the read loop's task group so the join below completes even
        # when the server has not closed the WebSocket. ``receive_bytes``
        # blocks indefinitely until the peer sends a frame; without this
        # cancel, exiting the context manager while the server is still
        # holding the connection open (the common case for ``stream()`` with
        # a long-running command) would deadlock.
        if self._task_group is not None:
            self._task_group.cancel_scope.cancel()
            self._task_group = None
        try:
            return await stack.__aexit__(exc_type, exc_value, traceback)
        except BaseExceptionGroup as eg:
            if len(eg.exceptions) == 1:
                raise eg.exceptions[0] from None
            raise

    def _before_cancel(self) -> None:
        """Called just before the read-loop task group is cancelled in ``__aexit__``.

        Override to close per-channel receive streams so the read loop
        unblocks promptly rather than waiting for the cancel scope to fire.
        """

    async def _send_frame(self, channel: int, payload: bytes) -> None:
        async with self._write_lock:
            await self._send_locked(channel, payload)

    async def _send_locked(self, channel: int, payload: bytes) -> None:
        """Send a frame assuming the write lock is already held."""
        if not self._open:
            raise KubexClientException("stream session is closed")
        frame = self._protocol.encode(channel, payload)
        await self._connection.send_bytes(frame)

    async def _send_data(self, channel: int, data: bytes) -> None:
        """Send ``data`` on ``channel`` as frames of at most 32 KiB.

        The write lock is taken per frame so control frames (e.g. resize) are
        not starved behind a large write; callers that need one write's
        frames to stay contiguous serialise writes to the channel themselves.
        """
        for chunk in _iter_chunks(data):
            async with self._write_lock:
                await self._send_locked(channel, chunk)

    async def _send_close_for_channel(self, target_channel_id: int) -> None:
        """Send a half-close frame for ``target_channel_id``.

        Idempotent: a second call for the same channel is a no-op.
        The half-close frame encoding is
        ``protocol.encode(CHANNEL_CLOSE, bytes([target_channel_id]))``.

        Protocols that do not support stream-close (e.g. v4 for portforward)
        skip the wire frame and only mark the channel locally — the kubelet
        ignores channel id 255 on those subprotocols. Once the session is
        closed the channel is likewise only marked locally.
        """
        async with self._write_lock:
            if target_channel_id in self._closed_channels:
                return
            if self._protocol.supports_close() and self._open:
                await self._send_locked(CHANNEL_CLOSE, bytes([target_channel_id]))
            self._closed_channels.add(target_channel_id)

    @abstractmethod
    async def _read_loop(self) -> None: ...


class _StdinWriter:
    """Writer for the stdin channel of a :class:`StreamSession`."""

    def __init__(self, session: StreamSession) -> None:
        self._session = session

    async def write(self, data: bytes) -> None:
        await self._session._send_stdin(data)

    async def close(self) -> None:
        await self._session.close_stdin()


class StreamSession(_BaseChannelSession):
    """Multiplexes Kubernetes channel-protocol streams over a single :class:`WebSocketConnection`.

    The session owns a background read loop that decodes incoming binary frames
    and dispatches their payloads to per-channel queues. Outgoing writes
    (``stdin``, ``resize``, ``close_stdin``) share a lock so concurrent callers
    do not interleave bytes on the underlying WebSocket.

    Inbound data is never dropped: when ``stdout`` or ``stderr`` has
    ``buffer_size`` undelivered frames, the read loop waits for the consumer,
    which also holds back every other channel (including the status). Drain
    each enabled channel concurrently, disable the ones you don't need
    (``stderr=False``), or close a receive stream (``session.stderr.close()``)
    to discard it. Leaving the ``async with`` block always tears the session
    down promptly, even while the read loop is waiting.

    Used by both the ``exec`` and ``attach`` subresource accessors.
    """

    def __init__(
        self,
        connection: WebSocketConnection,
        protocol: ChannelProtocol,
        *,
        stdin: bool = False,
        stdout: bool = True,
        stderr: bool = True,
        tty: bool = False,
        buffer_size: float = _DEFAULT_CHANNEL_BUFFER,
    ) -> None:
        super().__init__(connection, protocol)
        send_out, recv_out = anyio.create_memory_object_stream[bytes](
            max_buffer_size=buffer_size
        )
        send_err, recv_err = anyio.create_memory_object_stream[bytes](
            max_buffer_size=buffer_size
        )
        self._stdout_send: MemoryObjectSendStream[bytes] = send_out
        self._stdout_recv: MemoryObjectReceiveStream[bytes] = recv_out
        self._stderr_send: MemoryObjectSendStream[bytes] = send_err
        self._stderr_recv: MemoryObjectReceiveStream[bytes] = recv_err
        # Channels the kubelet will not open are closed locally up-front so
        # consumers iterating over ``stdout`` / ``stderr`` see an immediate
        # end-of-stream instead of blocking until socket teardown. The
        # kubelet merges stderr into stdout when ``tty=True`` and never
        # opens the dedicated stderr channel.
        self._stdout_open = stdout
        self._stderr_open = stderr and not tty
        if not self._stdout_open:
            self._stdout_send.close()
        if not self._stderr_open:
            self._stderr_send.close()
        self._status: Status | None = None
        self._status_event = anyio.Event()
        # Error-channel bytes collected until they form a complete Status
        # document (or the connection closes).
        self._error_buf = bytearray()
        self._stdin_enabled = stdin
        # When stdin is not enabled the channel was never opened, so writes
        # must fail locally and ``close_stdin`` must be a no-op (no CLOSE
        # frame on the wire for a channel that does not exist).
        self._stdin_closed = not stdin
        # Serialises stdin writes and the stdin half-close so one write's
        # frames stay contiguous; resize frames may still go in between.
        self._stdin_lock = anyio.Lock()
        self._stdin = _StdinWriter(self)

    def _before_cancel(self) -> None:
        self._stdout_recv.close()
        self._stderr_recv.close()

    @property
    def stdout(self) -> MemoryObjectReceiveStream[bytes]:
        """Stdout chunks as an async iterator; ends when the channel closes."""
        return self._stdout_recv

    @property
    def stderr(self) -> MemoryObjectReceiveStream[bytes]:
        """Stderr chunks as an async iterator; ends at once if disabled or with ``tty=True``."""
        return self._stderr_recv

    @property
    def stdin(self) -> _StdinWriter:
        """Writer for stdin: ``await stdin.write(data)``, ``await stdin.close()``.

        ``write()`` sends the data in frames of at most 32 KiB and raises
        ``RuntimeError`` if stdin was not enabled or is already closed.
        """
        return self._stdin

    @property
    def stdout_truncated(self) -> bool:
        """Deprecated: always ``False``.

        Output is no longer dropped when a consumer falls behind (the session
        applies backpressure instead), so there is nothing to report.
        """
        warnings.warn(
            "StreamSession.stdout_truncated is deprecated and always False: "
            "output is no longer dropped",
            DeprecationWarning,
            stacklevel=2,
        )
        return False

    @property
    def stderr_truncated(self) -> bool:
        """Deprecated: always ``False``. See :attr:`stdout_truncated`."""
        warnings.warn(
            "StreamSession.stderr_truncated is deprecated and always False: "
            "output is no longer dropped",
            DeprecationWarning,
            stacklevel=2,
        )
        return False

    async def wait_for_status(self) -> Status | None:
        """Wait for the terminal Status from the error channel.

        Resolves once a complete Status document has arrived, or when the
        connection closes; ``None`` means the server closed without sending
        one. The status only arrives after earlier frames have been
        delivered, so keep draining enabled output channels while waiting.

        Returns:
            Status | None: the reported ``Status``; error-channel text that is not
                a valid Status becomes a ``Failure`` Status carrying it. ``None``
                if the connection closed without any error-channel data.
        """
        await self._status_event.wait()
        return self._status

    async def resize(self, *, width: int, height: int) -> None:
        """Send a terminal resize event.

        Args:
            width: The new terminal width in columns; must be positive.
            height: The new terminal height in rows; must be positive.

        Raises:
            ValueError: ``width`` or ``height`` is not positive.
            KubexClientException: the session has already ended.
        """
        if width <= 0 or height <= 0:
            raise ValueError(
                f"resize requires positive width and height, got "
                f"width={width}, height={height}"
            )
        payload = json.dumps(
            {"Width": width, "Height": height}, separators=(",", ":")
        ).encode("utf-8")
        await self._send_frame(CHANNEL_RESIZE, payload)

    async def close_stdin(self) -> None:
        """Half-close stdin, signalling end-of-input to the process.

        Idempotent, and a no-op when stdin was not enabled.

        Raises:
            KubexClientException: stdin is still open but the session has
                already ended.
        """
        # Holding the stdin lock makes the check-then-send atomic with
        # respect to concurrent stdin writes, so no stdin frame can follow
        # the half-close on the wire. The flag is only set after the send
        # succeeds so a transient send failure leaves stdin open for retry.
        async with self._stdin_lock:
            if self._stdin_closed:
                return
            await self._send_frame(CHANNEL_CLOSE, bytes([CHANNEL_STDIN]))
            self._stdin_closed = True

    async def _send_stdin(self, data: bytes) -> None:
        async with self._stdin_lock:
            if not self._stdin_enabled:
                raise RuntimeError("stdin was not enabled for this stream session")
            if self._stdin_closed:
                raise RuntimeError("stdin is closed")
            await self._send_data(CHANNEL_STDIN, data)

    def _set_status(self, status: Status) -> None:
        self._status = status
        self._status_event.set()

    def _feed_error(self, payload: bytes) -> None:
        if self._status_event.is_set():
            return
        room = _MAX_ERROR_BYTES - len(self._error_buf)
        self._error_buf += payload[:room]
        try:
            doc = json.loads(self._error_buf)
        except ValueError:
            return  # incomplete document; wait for more frames or EOF
        self._set_status(_parse_status(self._error_buf, doc))

    def _finish_error(self) -> None:
        """Parse whatever the error channel carried once the connection closed."""
        if self._status_event.is_set() or not self._error_buf:
            return
        try:
            doc: Any = json.loads(self._error_buf)
        except ValueError as exc:
            _logger.debug("error channel carried a non-JSON payload: %s", exc)
            doc = None
        self._set_status(_parse_status(self._error_buf, doc))

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
                # Servers open each stream with an empty frame (on the error
                # channel when stdout/stderr are off); it carries nothing.
                if not payload:
                    continue
                if channel == CHANNEL_STDOUT:
                    if self._stdout_open:
                        self._stdout_open = await _dispatch(self._stdout_send, payload)
                elif channel == CHANNEL_STDERR:
                    if self._stderr_open:
                        self._stderr_open = await _dispatch(self._stderr_send, payload)
                elif channel == CHANNEL_ERROR:
                    self._feed_error(payload)
            self._finish_error()
        finally:
            self._stdout_send.close()
            self._stderr_send.close()
            self._status_event.set()
