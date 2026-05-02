from __future__ import annotations

import json
import sys
from abc import ABC, abstractmethod
from contextlib import AsyncExitStack
from types import TracebackType
from typing import TYPE_CHECKING

import anyio
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from kubex_core.models.status import Status
from pydantic import ValidationError

if sys.version_info < (3, 11):
    from exceptiongroup import BaseExceptionGroup

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

if TYPE_CHECKING:
    from typing_extensions import Self

__all__ = ["StreamSession", "_BaseChannelSession", "_resolve_protocol"]


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


# Per-channel bounded buffer for stdout / stderr. The read loop never blocks
# on a full buffer (see ``_read_loop``); instead it closes the channel locally
# so memory is bounded *and* sibling channels (notably the error channel and
# EOF detection) keep flowing. The cap trades hard data loss for a strict
# upper bound on client memory growth, which is the safer failure mode for an
# untrusted remote producer.
_DEFAULT_CHANNEL_BUFFER = 128


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
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        stack = self._exit_stack
        self._exit_stack = None
        if stack is None:
            return None
        # Subclasses close their per-channel receive ends here so that any
        # read-loop attempt to push to a closed receive side unblocks with
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
        frame = self._protocol.encode(channel, payload)
        async with self._write_lock:
            await self._connection.send_bytes(frame)

    async def _send_locked(self, channel: int, payload: bytes) -> None:
        """Send a frame assuming the write lock is already held."""
        frame = self._protocol.encode(channel, payload)
        await self._connection.send_bytes(frame)

    async def _send_close_for_channel(self, target_channel_id: int) -> None:
        """Send a half-close frame for ``target_channel_id``.

        Idempotent: a second call for the same channel is a no-op.
        The half-close frame encoding is
        ``protocol.encode(CHANNEL_CLOSE, bytes([target_channel_id]))``.

        Protocols that do not support stream-close (e.g. v4 for portforward)
        skip the wire frame and only mark the channel locally — the kubelet
        ignores channel id 255 on those subprotocols.
        """
        async with self._write_lock:
            if target_channel_id in self._closed_channels:
                return
            if self._protocol.supports_close():
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
        # Bounded per-channel buffers prevent unbounded memory growth when a
        # consumer enables a channel but drains it slower than the remote
        # produces. The read loop pushes via ``send_nowait`` and on
        # ``WouldBlock`` closes that channel locally — so the wire-reading
        # loop is never blocked (the error channel and EOF detection keep
        # flowing) and total client memory is strictly bounded. A consumer
        # that observes premature stream closure has fallen behind; re-running
        # with a slimmer command or tighter draining is the documented remedy.
        # ``run()`` opts out by passing ``buffer_size=math.inf`` because it
        # owns the lifecycle and collects all output in memory anyway — the
        # bounded-buffer drop semantics would silently truncate ``ExecResult``
        # if the read loop got a head start over the drainer tasks.
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
        # Per-channel overflow flags: set when ``_dispatch_nowait`` had to
        # close the channel locally because the bounded buffer was full.
        # Consumers iterating ``stdout`` / ``stderr`` only see an EOF, so
        # without these flags they cannot distinguish "command finished"
        # from "we fell behind and lost output". Check after iteration ends.
        self._stdout_truncated = False
        self._stderr_truncated = False
        self._status: Status | None = None
        self._status_event = anyio.Event()
        self._stdin_enabled = stdin
        # When stdin is not enabled the channel was never opened, so writes
        # must fail locally and ``close_stdin`` must be a no-op (no CLOSE
        # frame on the wire for a channel that does not exist).
        self._stdin_closed = not stdin
        self._stdin = _StdinWriter(self)

    def _before_cancel(self) -> None:
        self._stdout_recv.close()
        self._stderr_recv.close()

    @property
    def stdout(self) -> MemoryObjectReceiveStream[bytes]:
        return self._stdout_recv

    @property
    def stderr(self) -> MemoryObjectReceiveStream[bytes]:
        return self._stderr_recv

    @property
    def stdin(self) -> _StdinWriter:
        return self._stdin

    @property
    def stdout_truncated(self) -> bool:
        """``True`` if the stdout buffer overflowed and frames were dropped.

        Consumers should check this after ``session.stdout`` ends to tell
        a normal EOF apart from a local close triggered by backpressure.
        See the buffer-management note on ``__init__``.
        """
        return self._stdout_truncated

    @property
    def stderr_truncated(self) -> bool:
        """``True`` if the stderr buffer overflowed and frames were dropped.

        Counterpart to :attr:`stdout_truncated`.
        """
        return self._stderr_truncated

    async def wait_for_status(self) -> Status | None:
        """Wait for a terminal Status from the error channel.

        Resolves to ``None`` if the connection closes before any error frame
        arrives.
        """
        await self._status_event.wait()
        return self._status

    async def resize(self, *, width: int, height: int) -> None:
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
        # Acquire the write lock *before* checking the flag so the
        # check-then-send is atomic with respect to concurrent stdin
        # writes. Without this, a writer that snapshotted the flag as
        # ``False`` could still emit a stdin frame after the close
        # frame was sent on the wire — violating the half-close
        # contract. The flag is only set after the send succeeds so a
        # transient send failure leaves stdin open for retry.
        async with self._write_lock:
            if self._stdin_closed:
                return
            await self._send_locked(CHANNEL_CLOSE, bytes([CHANNEL_STDIN]))
            self._stdin_closed = True

    async def _send_stdin(self, data: bytes) -> None:
        # Lock first, then check the closed flag, so close_stdin cannot
        # interleave a close frame between this write's flag-check and
        # send. See ``close_stdin`` for the matching half-close contract.
        async with self._write_lock:
            if not self._stdin_enabled:
                raise RuntimeError("stdin was not enabled for this stream session")
            if self._stdin_closed:
                raise RuntimeError("stdin is closed")
            await self._send_locked(CHANNEL_STDIN, data)

    @staticmethod
    def _dispatch_nowait(
        send_stream: MemoryObjectSendStream[bytes], payload: bytes
    ) -> tuple[bool, bool]:
        """Push ``payload`` to ``send_stream`` without blocking the read loop.

        Returns a ``(still_open, truncated)`` tuple: ``still_open`` is
        ``False`` if the channel has been closed (either by the consumer or
        because the buffer was full and we just closed it locally to bound
        memory growth); ``truncated`` is ``True`` only when *this* call closed
        the channel due to a full buffer (the OOM-prevention drop path).
        """
        try:
            send_stream.send_nowait(payload)
            return True, False
        except anyio.WouldBlock:
            # Buffer full — close the send side so the consumer observes
            # end-of-stream instead of silently losing arbitrary frames.
            # This is the documented data-loss / OOM-prevention trade-off,
            # surfaced to consumers via the per-channel ``*_truncated`` flags.
            send_stream.close()
            return False, True
        except (anyio.BrokenResourceError, anyio.ClosedResourceError):
            # Consumer dropped this channel; stop pushing to it but keep
            # processing other channels (notably error / EOF).
            return False, False

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
                if channel == CHANNEL_STDOUT:
                    if self._stdout_open:
                        still_open, truncated = self._dispatch_nowait(
                            self._stdout_send, payload
                        )
                        self._stdout_open = still_open
                        if truncated:
                            self._stdout_truncated = True
                elif channel == CHANNEL_STDERR:
                    if self._stderr_open:
                        still_open, truncated = self._dispatch_nowait(
                            self._stderr_send, payload
                        )
                        self._stderr_open = still_open
                        if truncated:
                            self._stderr_truncated = True
                elif channel == CHANNEL_ERROR:
                    if payload and self._status is None:
                        try:
                            self._status = Status.model_validate_json(payload)
                        except ValidationError:
                            pass
                    self._status_event.set()
        finally:
            self._stdout_send.close()
            self._stderr_send.close()
            if not self._status_event.is_set():
                self._status_event.set()
