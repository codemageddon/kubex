from __future__ import annotations

import math
import sys
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncIterator, Generic, Sequence, Type, TypeVar, overload

import anyio

if sys.version_info < (3, 11):
    from exceptiongroup import BaseExceptionGroup

from kubex.api._stream_session import StreamSession, _resolve_protocol
from kubex.client.client import BaseClient
from kubex.core.exceptions import KubexClientException
from kubex.core.exec_channels import (
    DEFAULT_PROTOCOLS,
    ChannelProtocol,
)
from kubex.core.params import ExecOptions, NamespaceTypes, Timeout
from kubex.core.request_builder.builder import RequestBuilder
from kubex_core.models.interfaces import HasExec
from kubex_core.models.resource_config import Scope
from kubex_core.models.status import Status
from kubex_core.models.typing import ResourceType

from ._protocol import (
    ApiNamespaceTypes,
    ApiProtocol,
    ApiRequestTimeoutTypes,
    CachedSubresourceDescriptor,
    SubresourceNotAvailable,
    ensure_required_namespace,
)

__all__ = [
    "ExecAccessor",
    "ExecResult",
    "_ExecDescriptor",
]

_E = TypeVar("_E", bound=HasExec)


@dataclass
class ExecResult:
    """Result of a one-shot ``ExecAccessor.run`` call."""

    stdout: bytes
    stderr: bytes
    status: Status | None = None

    @property
    def exit_code(self) -> int | None:
        """Parse the exit code from ``status``.

        Returns ``0`` for a ``Success`` status, the integer parsed from
        ``status.details.causes`` (where ``reason == "ExitCode"``) for a
        non-zero exit, or ``None`` when ``status`` is missing or carries no
        recognisable exit information. Note that ``None`` does not imply
        success — for failures without a recognisable exit code (e.g. the
        container could not start), inspect ``status`` directly.
        """
        return _parse_exit_code(self.status)


def _parse_exit_code(status: Status | None) -> int | None:
    if status is None:
        return None
    if status.status == "Success":
        return 0
    details = status.details
    if details is None or details.causes is None:
        return None
    for cause in details.causes:
        if cause.reason == "ExitCode":
            try:
                return int(cause.message)
            except (TypeError, ValueError):
                return None
    return None


class ExecAccessor(Generic[ResourceType]):
    """Accessor for the Pod ``exec`` subresource."""

    def __init__(
        self,
        client: BaseClient,
        request_builder: RequestBuilder,
        namespace: NamespaceTypes,
        scope: Scope,
        resource_type: Type[ResourceType],
        channel_protocols: tuple[ChannelProtocol, ...] = DEFAULT_PROTOCOLS,
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
        command: Sequence[str],
        container: str | None,
        namespace: ApiNamespaceTypes,
        stdin: bool,
        stdout: bool,
        stderr: bool,
        tty: bool,
        request_timeout: ApiRequestTimeoutTypes,
        buffer_size: float | None,
    ) -> StreamSession:
        _namespace = ensure_required_namespace(namespace, self._namespace, self._scope)
        options = ExecOptions(
            command=command,
            container=container,
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            tty=tty,
        )
        request = self._request_builder.exec_request(
            name, _namespace, options, request_timeout=request_timeout
        )
        subprotocols = [p.subprotocol for p in self._channel_protocols]
        connection = await self._client.connect_websocket(
            request, subprotocols=subprotocols
        )
        try:
            protocol = _resolve_protocol(connection, self._channel_protocols)
            kwargs: dict[str, Any] = {
                "stdin": stdin,
                "stdout": stdout,
                "stderr": stderr,
                "tty": tty,
            }
            if buffer_size is not None:
                kwargs["buffer_size"] = buffer_size
            return StreamSession(connection, protocol, **kwargs)
        except BaseException:
            # Suppress cleanup errors so the original exception (e.g. an
            # unsupported-subprotocol ``KubexClientException``) is preserved
            # for the caller rather than being masked by a transport-level
            # failure during the close path. ``except Exception`` (not
            # ``BaseException``) so a ``Cancelled`` raised during the close —
            # because the surrounding scope was cancelled — propagates and
            # cooperative cancellation is not silently dropped.
            try:
                await connection.close()
            except Exception:
                pass
            raise

    @asynccontextmanager
    async def stream(
        self,
        name: str,
        *,
        command: Sequence[str],
        container: str | None = None,
        namespace: ApiNamespaceTypes = Ellipsis,
        stdin: bool = False,
        stdout: bool = True,
        stderr: bool = True,
        tty: bool = False,
        request_timeout: ApiRequestTimeoutTypes = Ellipsis,
    ) -> AsyncIterator[StreamSession]:
        """Open a bidirectional exec session as an async context manager."""
        session = await self._open_session(
            name,
            command=command,
            container=container,
            namespace=namespace,
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            tty=tty,
            request_timeout=request_timeout,
            buffer_size=None,
        )
        async with session:
            yield session

    async def run(
        self,
        name: str,
        *,
        command: Sequence[str],
        container: str | None = None,
        namespace: ApiNamespaceTypes = Ellipsis,
        stdin: bytes | None = None,
        stdout: bool = True,
        stderr: bool = True,
        request_timeout: ApiRequestTimeoutTypes = Ellipsis,
    ) -> ExecResult:
        """Run a command and collect stdout/stderr until the channel closes.

        Unlike :meth:`stream`, the ``request_timeout`` bound (when provided)
        applies to both the handshake (via the per-call HTTP timeout
        propagated to the WebSocket upgrade) and the post-handshake command
        execution + status collection (via a separate wall-clock cancel scope
        that does not envelope teardown — see below). The wall-clock bound is
        derived from ``Timeout.total`` if set, otherwise ``Timeout.read``
        (read's strict per-byte-inactivity semantics do not map cleanly onto
        a long-lived WebSocket session, so it is treated as a call-level
        upper bound here as a pragmatic approximation that prevents
        indefinite hangs). ``Ellipsis`` defers to the client default for the
        handshake without imposing an additional wall-clock bound; an
        explicit ``None`` disables timeouts entirely.
        """
        # Resolve the wall-clock bound for the post-handshake portion.
        # ``Ellipsis`` and a ``Timeout`` whose ``total`` and ``read`` are
        # both unset leave ``delay`` as ``None`` — ``anyio.fail_after(None)``
        # is a no-op cancel scope, so the only bound on the call in those
        # cases is whatever the handshake timeout enforces (set via
        # ``request_timeout`` propagation below).
        delay: float | None = None
        if request_timeout is not Ellipsis:
            coerced: Timeout | None = Timeout.coerce(request_timeout)
            if coerced is not None:
                delay = coerced.total if coerced.total is not None else coerced.read

        # Bypass ``stream()`` to use unbounded per-channel buffers. The
        # default bounded buffers exist to apply backpressure when the
        # consumer iterates lazily; ``run()`` instead spawns drainer tasks
        # that race with the read loop, and the read loop is started in
        # ``StreamSession.__aenter__`` *before* those drainers are scheduled.
        # That scheduling gap means a fast command emitting many frames
        # could fill the bounded buffer and trigger the local
        # close-on-overflow path before the drainers ran even once,
        # silently truncating ``ExecResult.stdout`` / ``stderr``. Unbounded
        # buffers are safe here because ``run`` collects all output in
        # memory anyway — OOM risk is identical.
        #
        # The handshake is bounded by ``request_timeout`` propagation into
        # the per-backend WebSocket upgrade (see ``HttpxClient`` /
        # ``AioHttpClient``). The wall-clock ``fail_after`` below covers
        # only the post-handshake portion — keeping it *outside* the
        # ``async with session`` block ensures ``StreamSession.__aexit__``
        # (and the underlying ``connection.close()``) runs in an
        # un-cancelled scope so the HTTP/WebSocket transport is always
        # released, even when the deadline fires mid-call.
        session = await self._open_session(
            name,
            command=command,
            container=container,
            namespace=namespace,
            stdin=stdin is not None,
            stdout=stdout,
            stderr=stderr,
            tty=False,
            request_timeout=request_timeout,
            buffer_size=math.inf,
        )
        async with session:
            stdout_buf = bytearray()
            stderr_buf = bytearray()
            status: Status | None = None

            async def _drain_stdout() -> None:
                async for chunk in session.stdout:
                    stdout_buf.extend(chunk)

            async def _drain_stderr() -> None:
                async for chunk in session.stderr:
                    stderr_buf.extend(chunk)

            async def _write_stdin() -> None:
                if stdin is not None:
                    await session.stdin.write(stdin)
                    await session.close_stdin()

            # ``anyio.fail_after`` raises a bare ``TimeoutError`` at scope
            # exit when the deadline fires. The exec layer normalises every
            # other WebSocket-level failure to ``KubexClientException``
            # (see ``_resolve_protocol`` and the per-backend handshake
            # handlers), so convert here too — callers that
            # ``except KubexClientException`` for exec errors must observe
            # a timed-out ``run()`` consistently.
            try:
                with anyio.fail_after(delay):
                    async with anyio.create_task_group() as tg:
                        tg.start_soon(_drain_stdout)
                        tg.start_soon(_drain_stderr)
                        tg.start_soon(_write_stdin)

                    status = await session.wait_for_status()
            except TimeoutError as exc:
                raise KubexClientException(
                    f"exec call exceeded {delay}s wall-clock bound"
                ) from exc
            except BaseExceptionGroup as eg:
                # anyio 4 wraps exceptions raised by tasks in a task group
                # in a ``BaseExceptionGroup`` even when only a single task
                # failed. Unwrap a single-exception group so callers that
                # catch ``KubexClientException`` (the documented exec
                # exception type) observe transport-level failures from
                # ``_drain_*`` or ``_write_stdin`` directly instead of
                # having to reach into an exception group.
                if len(eg.exceptions) == 1:
                    raise eg.exceptions[0] from None
                raise
        return ExecResult(
            stdout=bytes(stdout_buf), stderr=bytes(stderr_buf), status=status
        )


class _ExecDescriptor(CachedSubresourceDescriptor):
    _marker = HasExec
    _accessor_cls = ExecAccessor
    _error_message = "Exec is only supported for resources with HasExec marker"

    @overload
    def __get__(self, instance: None, owner: type) -> _ExecDescriptor: ...

    @overload
    def __get__(self, instance: ApiProtocol[_E], owner: type) -> ExecAccessor[_E]: ...

    @overload
    def __get__(
        self, instance: ApiProtocol[Any], owner: type
    ) -> SubresourceNotAvailable: ...

    def __get__(self, instance: Any, owner: type | None = None) -> Any:
        return self._resolve(instance)
