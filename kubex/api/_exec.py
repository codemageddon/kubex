from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncIterator, Generic, Self, Sequence, Type, TypeVar, overload

import anyio
from anyio.streams.memory import MemoryObjectReceiveStream

from kubex.api._stream_session import StreamSession, _resolve_protocol
from kubex.client.client import BaseClient
from kubex.core.exceptions import KubexClientException, KubexTimeoutError
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
    "ExecError",
    "ExecResult",
    "_ExecDescriptor",
]

_E = TypeVar("_E", bound=HasExec)

_logger = logging.getLogger("kubex.exec")


class ExecError(KubexClientException):
    """Raised by :meth:`ExecResult.raise_for_status` when a command did not succeed.

    The message is the server's ``Status.message`` when there is one; the full
    result (output, ``status``, ``exit_code``) is available as ``result``.
    """

    def __init__(self, message: str, result: ExecResult) -> None:
        super().__init__(message)
        self.result = result

    @property
    def status(self) -> Status | None:
        """The failed command's ``Status``, or ``None`` if none was reported."""
        return self.result.status

    @property
    def exit_code(self) -> int | None:
        """The failed command's exit code, or ``None``; see :attr:`ExecResult.exit_code`."""
        return self.result.exit_code


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
        container could not start), inspect ``status`` directly, or call
        :meth:`raise_for_status`.
        """
        return _parse_exit_code(self.status)

    def raise_for_status(self) -> Self:
        """Raise :class:`ExecError` unless the command reported ``Success``.

        Covers non-zero exits as well as failures without an exit code (e.g.
        the binary does not exist) and a missing status. Returns ``self`` so
        it can be chained: ``(await api.exec.run(...)).raise_for_status()``.

        Returns:
            Self: this result, unchanged, when the status is ``Success``.

        Raises:
            ExecError: the status is missing or is not ``Success``. Its message is
                the server's ``Status.message`` (or ``reason``) when there is one.
        """
        status = self.status
        if status is not None and status.status == "Success":
            return self
        if status is None:
            message = "exec finished without reporting a status"
        else:
            message = status.message or status.reason or "exec failed"
        raise ExecError(message, self)


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
            if cause.message is None:
                return None
            try:
                return int(cause.message)
            except ValueError:
                return None
    return None


class ExecAccessor(Generic[ResourceType]):
    """Accessor for the Pod ``exec`` subresource.

    .. warning::

       **Experimental.** The WebSocket-based subresources (``exec``,
       ``attach``, ``portforward``) are still under active development and
       their API may change in future releases without notice.
    """

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
            return StreamSession(
                connection,
                protocol,
                stdin=stdin,
                stdout=stdout,
                stderr=stderr,
                tty=tty,
            )
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
        """Open a bidirectional exec session as an async context manager.

        .. warning::

           **Experimental.** This WebSocket-based API is still under active
           development and may change in future releases without notice.

        Output is never dropped: a channel whose consumer falls behind pauses
        the whole session (backpressure). Drain every enabled output channel
        concurrently, or disable the ones you don't need (e.g.
        ``stderr=False``).

        Leaving the ``async with`` block closes the session, even while the
        command is still running.

        Args:
            name: The name of the Pod to run the command in.
            command: The command and its arguments, e.g. ``["sh", "-c", "ls"]``.
                Must be a non-empty sequence of strings, not a single string.
            container: The container to run the command in. Required when the Pod
                has more than one container.
            namespace: The namespace of the Pod. If not provided,
                the namespace provided when creating the API will be used.
                The namespace is required for namespaced resources.
                If namespace is provided for cluster-scoped resources, an error will be raised.
            stdin: Open the stdin channel, for writing with ``session.stdin``.
            stdout: Open the stdout channel.
            stderr: Open the stderr channel. Ignored with ``tty=True``.
            tty: Allocate a pseudo-terminal. The kubelet then merges stderr into
                stdout, so ``session.stderr`` closes immediately.
            request_timeout: HTTP-level timeout override for the WebSocket
                handshake. A number is interpreted as the total timeout in
                seconds. Pass ``None`` to disable timeouts entirely. Omit to use
                the client default. It does not bound the session itself.

        Yields:
            StreamSession: the open session, with ``stdin``, ``stdout``,
                ``stderr``, ``resize()``, ``close_stdin()`` and
                ``wait_for_status()``.

        Raises:
            ValueError: an argument is invalid, e.g. an empty or malformed ``name``,
                or a namespace that is missing for a namespace-scoped resource or
                given for a cluster-scoped one; or ``command`` is empty.
            TypeError: ``command`` is a single string (or bytes) instead of a
                sequence of strings, or contains a non-string item.
            KubexApiError: the WebSocket handshake was rejected; the subclass matches
                the HTTP status (e.g. ``NotFound`` for a missing pod, ``BadRequest``
                for an unknown container, ``Forbidden``).
            KubexConnectionError: the API server could not be reached.
            KubexTimeoutError: the WebSocket handshake timed out.
            KubexClientException: the WebSocket handshake failed for another reason,
                or the connection closed abnormally.
            ConfigurationError: credentials could not be obtained, or the httpx
                client is used without the ``httpx-ws`` extra installed.
        """
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

        .. warning::

           **Experimental.** This WebSocket-based API is still under active
           development and may change in future releases without notice.

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

        ``stdin`` is sent in frames of at most 32 KiB and then half-closed. A
        failure while sending it (e.g. the command exited without reading
        all of it) is logged, not raised: the result reflects what the
        server reported. Use :meth:`ExecResult.raise_for_status` to turn a
        non-successful status into an exception.

        Args:
            name: The name of the Pod to run the command in.
            command: The command and its arguments, e.g. ``["cat", "/etc/hostname"]``.
                Must be a non-empty sequence of strings, not a single string.
            container: The container to run the command in. Required when the Pod
                has more than one container.
            namespace: The namespace of the Pod. If not provided,
                the namespace provided when creating the API will be used.
                The namespace is required for namespaced resources.
                If namespace is provided for cluster-scoped resources, an error will be raised.
            stdin: Bytes to send to the command's stdin, which is then closed.
                ``None`` (the default) does not open a stdin channel at all;
                ``b""`` opens it and closes it right away.
            stdout: Capture stdout.
            stderr: Capture stderr.
            request_timeout: Timeout override for this call, bounding both the
                handshake and the command's run; see above. A number is
                interpreted as the total timeout in seconds. Pass ``None`` to
                disable timeouts entirely. Omit to use the client default for the
                handshake only.

        Returns:
            ExecResult: the captured ``stdout`` and ``stderr`` bytes and the
                ``status`` the server reported (``None`` if it reported none).

        Raises:
            ValueError: an argument is invalid, e.g. an empty or malformed ``name``,
                or a namespace that is missing for a namespace-scoped resource or
                given for a cluster-scoped one; or ``command`` is empty.
            TypeError: ``command`` is a single string (or bytes) instead of a
                sequence of strings, or contains a non-string item.
            KubexApiError: the WebSocket handshake was rejected; the subclass matches
                the HTTP status (e.g. ``NotFound`` for a missing pod, ``BadRequest``
                for an unknown container, ``Forbidden``).
            KubexConnectionError: the API server could not be reached.
            KubexTimeoutError: the WebSocket handshake or the command did not finish
                within ``request_timeout``.
            KubexClientException: the WebSocket handshake failed for another reason,
                or the connection closed abnormally.
            ConfigurationError: credentials could not be obtained, or the httpx
                client is used without the ``httpx-ws`` extra installed.
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

        # The handshake is bounded by ``request_timeout`` propagation into
        # the per-backend WebSocket upgrade (see ``HttpxClient`` /
        # ``AioHttpClient``). The wall-clock ``fail_after`` below covers
        # only the post-handshake portion — keeping it *inside* the
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
        )
        stdout_buf = bytearray()
        stderr_buf = bytearray()
        status: Status | None = None
        async with session:

            async def _drain(
                stream: MemoryObjectReceiveStream[bytes], buf: bytearray
            ) -> None:
                async for chunk in stream:
                    buf.extend(chunk)

            async def _write_stdin(data: bytes) -> None:
                # Like client-go, a failed stdin copy does not decide the
                # outcome: the command may have exited without reading all
                # of its input, and the read side still reports its status.
                # A broken connection surfaces there as well.
                try:
                    await session.stdin.write(data)
                    await session.close_stdin()
                except Exception as exc:
                    _logger.debug("exec stdin write failed: %r", exc)

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
                        if stdin is not None:
                            tg.start_soon(_write_stdin, stdin)
                        # Both channels are drained concurrently: the read
                        # loop waits for a full channel, so draining only one
                        # could stall the session.
                        async with anyio.create_task_group() as readers:
                            readers.start_soon(_drain, session.stdout, stdout_buf)
                            readers.start_soon(_drain, session.stderr, stderr_buf)
                        status = await session.wait_for_status()
                        # The command has finished; unsent stdin is moot.
                        tg.cancel_scope.cancel()
            except TimeoutError as exc:
                raise KubexTimeoutError(
                    f"exec call exceeded {delay}s wall-clock bound"
                ) from exc
            except BaseExceptionGroup as eg:
                # anyio 4 wraps exceptions raised by tasks in a task group
                # in a ``BaseExceptionGroup`` even when only a single task
                # failed. Unwrap a single-exception group so callers that
                # catch ``KubexClientException`` (the documented exec
                # exception type) observe failures directly instead of
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
