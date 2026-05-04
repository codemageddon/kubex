from __future__ import annotations

import json
from typing import Any, Sequence

import anyio
import pytest

from kubex.api._exec import ExecAccessor, ExecResult
from kubex.client.client import BaseClient
from kubex.client.options import ClientOptions
from kubex.client.websocket import WebSocketConnection
from kubex.core.exceptions import KubexClientException
from kubex.core.exec_channels import V5ChannelProtocol
from kubex.core.params import Timeout
from kubex.core.request import Request
from kubex.core.request_builder.builder import RequestBuilder
from kubex.k8s.v1_35.core.v1.pod import Pod
from kubex_core.models.resource_config import Scope
from kubex_core.models.status import Status


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class _FakeWebSocket(WebSocketConnection):
    """In-memory WebSocketConnection feeding pre-staged frames."""

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


class _FakeClient(BaseClient):
    """Stub BaseClient that yields a preconfigured WebSocketConnection."""

    def __init__(self, websocket: WebSocketConnection) -> None:
        self._websocket = websocket
        self.connect_calls: list[tuple[Request, list[str]]] = []
        self._options = ClientOptions()

    def _create_inner_client(self) -> Any:  # pragma: no cover - never invoked
        return object()

    async def request(self, request: Request) -> Any:  # pragma: no cover
        raise AssertionError("request should not be called for exec")

    def stream_lines(self, request: Request) -> Any:  # pragma: no cover
        raise AssertionError("stream_lines should not be called for exec")

    async def close(self) -> None:
        return None

    async def connect_websocket(
        self, request: Request, subprotocols: Sequence[str]
    ) -> WebSocketConnection:
        self.connect_calls.append((request, list(subprotocols)))
        return self._websocket


def _accessor_for_pod(client: BaseClient) -> ExecAccessor[Pod]:
    builder = RequestBuilder(resource_config=Pod.__RESOURCE_CONFIG__)
    return ExecAccessor(
        client=client,
        request_builder=builder,
        namespace="default",
        scope=Scope.NAMESPACE,
        resource_type=Pod,
    )


@pytest.mark.anyio
async def test_stream_builds_request_with_v5_subprotocol() -> None:
    ws = _FakeWebSocket()
    ws.feed_eof()
    client = _FakeClient(ws)
    accessor = _accessor_for_pod(client)

    async with accessor.stream("my-pod", command=["sh"]) as session:
        assert session is not None

    assert len(client.connect_calls) == 1
    request, subprotocols = client.connect_calls[0]
    assert request.method == "GET"
    assert request.url.endswith("/pods/my-pod/exec")
    assert "namespaces/default" in request.url
    assert subprotocols == [V5ChannelProtocol.subprotocol]


@pytest.mark.anyio
async def test_stream_passes_command_and_options_to_request() -> None:
    ws = _FakeWebSocket()
    ws.feed_eof()
    client = _FakeClient(ws)
    accessor = _accessor_for_pod(client)

    async with accessor.stream(
        "my-pod",
        command=["echo", "hi"],
        container="app",
        stdin=True,
        tty=True,
    ):
        pass

    request, _ = client.connect_calls[0]
    assert request.query_param_pairs is not None
    pairs = request.query_param_pairs
    assert ("command", "echo") in pairs
    assert ("command", "hi") in pairs
    assert ("container", "app") in pairs
    assert ("stdin", "true") in pairs
    assert ("tty", "true") in pairs
    assert ("stdout", "true") in pairs
    assert ("stderr", "true") in pairs


@pytest.mark.anyio
async def test_stream_closes_websocket_on_exit() -> None:
    ws = _FakeWebSocket()
    ws.feed_eof()
    client = _FakeClient(ws)
    accessor = _accessor_for_pod(client)

    async with accessor.stream("my-pod", command=["sh"]):
        assert not ws.closed
    assert ws.closed


@pytest.mark.anyio
async def test_stream_closes_websocket_on_exception() -> None:
    ws = _FakeWebSocket()
    ws.feed_eof()
    client = _FakeClient(ws)
    accessor = _accessor_for_pod(client)

    with pytest.raises(RuntimeError, match="boom"):
        async with accessor.stream("my-pod", command=["sh"]):
            raise RuntimeError("boom")
    assert ws.closed


@pytest.mark.anyio
async def test_run_collects_stdout_stderr_and_status() -> None:
    ws = _FakeWebSocket()
    ws.feed(bytes([1]) + b"hello\n")
    ws.feed(bytes([2]) + b"warn\n")
    status_payload = json.dumps(
        {
            "apiVersion": "v1",
            "kind": "Status",
            "metadata": {},
            "status": "Success",
        }
    ).encode()
    ws.feed(bytes([3]) + status_payload)
    ws.feed_eof()

    client = _FakeClient(ws)
    accessor = _accessor_for_pod(client)

    result = await accessor.run("my-pod", command=["echo", "hello"])

    assert isinstance(result, ExecResult)
    assert result.stdout == b"hello\n"
    assert result.stderr == b"warn\n"
    assert result.status is not None
    assert result.status.status == "Success"
    assert ws.closed


@pytest.mark.anyio
async def test_run_writes_stdin_then_closes_it() -> None:
    ws = _FakeWebSocket()
    ws.feed(bytes([1]) + b"piped\n")
    status_payload = json.dumps(
        {"apiVersion": "v1", "kind": "Status", "metadata": {}, "status": "Success"}
    ).encode()
    ws.feed(bytes([3]) + status_payload)
    ws.feed_eof()

    client = _FakeClient(ws)
    accessor = _accessor_for_pod(client)

    result = await accessor.run("my-pod", command=["cat"], stdin=b"piped\n")
    assert result.stdout == b"piped\n"
    # stdin frame: channel 0
    assert any(frame == bytes([0]) + b"piped\n" for frame in ws.sent)
    # close stdin frame: 255 0
    assert any(frame == bytes([255, 0]) for frame in ws.sent)


@pytest.mark.anyio
async def test_run_request_enables_stdin_when_payload_provided() -> None:
    ws = _FakeWebSocket()
    status_payload = json.dumps(
        {"apiVersion": "v1", "kind": "Status", "metadata": {}, "status": "Success"}
    ).encode()
    ws.feed(bytes([3]) + status_payload)
    ws.feed_eof()

    client = _FakeClient(ws)
    accessor = _accessor_for_pod(client)
    await accessor.run("my-pod", command=["cat"], stdin=b"x")

    request, _ = client.connect_calls[0]
    assert request.query_param_pairs is not None
    assert ("stdin", "true") in request.query_param_pairs


@pytest.mark.anyio
async def test_run_with_no_status_returns_none() -> None:
    ws = _FakeWebSocket()
    ws.feed(bytes([1]) + b"out")
    ws.feed_eof()
    client = _FakeClient(ws)
    accessor = _accessor_for_pod(client)

    result = await accessor.run("my-pod", command=["echo"])
    assert result.stdout == b"out"
    assert result.status is None


def _status_with_exit_code(code: str) -> Status:
    return Status.model_validate(
        {
            "apiVersion": "v1",
            "kind": "Status",
            "metadata": {},
            "status": "Failure",
            "reason": "NonZeroExitCode",
            "message": "command terminated with non-zero exit code",
            "details": {
                "causes": [
                    {"reason": "ExitCode", "message": code},
                ],
            },
        }
    )


def test_exec_result_exit_code_parses_from_status_details() -> None:
    status = _status_with_exit_code("7")
    result = ExecResult(stdout=b"", stderr=b"", status=status)
    assert result.exit_code == 7


def test_exec_result_exit_code_returns_zero_for_success() -> None:
    status = Status.model_validate(
        {"apiVersion": "v1", "kind": "Status", "metadata": {}, "status": "Success"}
    )
    result = ExecResult(stdout=b"", stderr=b"", status=status)
    assert result.exit_code == 0


def test_exec_result_exit_code_none_when_status_missing() -> None:
    result = ExecResult(stdout=b"", stderr=b"", status=None)
    assert result.exit_code is None


@pytest.mark.anyio
async def test_stream_raises_kubex_client_exception_for_unsupported_subprotocol() -> (
    None
):
    """Regression: ``select_protocol`` raises ``ValueError`` for an unknown
    server-selected subprotocol; the accessor must normalise this to the
    documented ``KubexClientException`` and close the underlying socket."""
    ws = _FakeWebSocket(subprotocol="unknown.protocol.k8s.io")
    ws.feed_eof()
    client = _FakeClient(ws)
    accessor = _accessor_for_pod(client)

    with pytest.raises(KubexClientException, match="unsupported subprotocol"):
        async with accessor.stream("my-pod", command=["sh"]):
            pass

    assert ws.closed


def test_exec_result_exit_code_none_when_unparseable() -> None:
    status = Status.model_validate(
        {
            "apiVersion": "v1",
            "kind": "Status",
            "metadata": {},
            "status": "Failure",
            "reason": "InternalError",
        }
    )
    result = ExecResult(stdout=b"", stderr=b"", status=status)
    assert result.exit_code is None


@pytest.mark.anyio
async def test_run_collects_all_output_under_burst_load() -> None:
    """Regression: ``run()`` must not truncate output when the read loop
    starts before drainer tasks. Earlier the bounded per-channel buffer
    (default 128 frames) would close-on-overflow during the scheduling gap
    between ``StreamSession.__aenter__`` (starts the read loop) and the
    drainers' ``start_soon`` calls in ``run()``. The fix is unbounded
    buffers in the ``run()`` path — OOM risk is unchanged because
    ``ExecResult`` already collects everything in memory."""
    burst = 1000
    chunk = b"x" * 16
    ws = _FakeWebSocket(buffer=burst + 8)
    for _ in range(burst):
        ws.feed(bytes([1]) + chunk)
    status_payload = json.dumps(
        {"apiVersion": "v1", "kind": "Status", "metadata": {}, "status": "Success"}
    ).encode()
    ws.feed(bytes([3]) + status_payload)
    ws.feed_eof()

    client = _FakeClient(ws)
    accessor = _accessor_for_pod(client)

    result = await accessor.run("my-pod", command=["echo"])

    assert result.stdout == chunk * burst
    assert result.status is not None
    assert result.status.status == "Success"


@pytest.mark.anyio
async def test_run_honors_read_timeout_as_wall_clock_fallback() -> None:
    """Regression: ``run()`` previously only applied ``Timeout.total`` as the
    wall-clock bound. A caller passing ``Timeout(read=X)`` (no ``total``) got
    handshake-only bounding, so a hung exec stream could block ``run()``
    forever. The fix uses ``read`` as the call-level upper bound when
    ``total`` is unset, and the deadline surfaces as ``KubexClientException``
    to match the exec layer's documented exception type."""
    ws = _FakeWebSocket()
    # Deliberately do NOT feed EOF or a status frame — the read loop will
    # block on ``receive_bytes`` indefinitely. Without the fallback ``run()``
    # would hang past the test timeout.
    client = _FakeClient(ws)
    accessor = _accessor_for_pod(client)

    with anyio.fail_after(5.0):
        with pytest.raises(KubexClientException, match="wall-clock bound"):
            await accessor.run(
                "my-pod",
                command=["sleep", "100"],
                request_timeout=Timeout(read=0.2),
            )

    # Teardown must complete even when the deadline fires inside
    # ``async with session`` — otherwise the underlying HTTP/WebSocket
    # transport leaks and repeated timed-out execs would accumulate stuck
    # connections in the client pool.
    assert ws.closed


@pytest.mark.anyio
async def test_run_drives_connection_close_to_completion_on_timeout() -> None:
    """Regression: when ``run()``'s wall-clock ``fail_after`` fires inside
    ``async with session``, ``StreamSession.__aexit__`` must drive the backend
    ``connection.close()`` to completion. Without shielding, awaits inside
    close run in an already-cancelled scope and are interrupted mid-flight,
    leaking the underlying HTTP/WebSocket transport."""

    class _SlowCloseWebSocket(_FakeWebSocket):
        def __init__(self) -> None:
            super().__init__()
            self.close_finished = False

        async def close(self) -> None:
            # Real backends do at least one ``await`` during close (sending a
            # close frame, awaiting peer ack). This simulates that await so an
            # unshielded teardown would observe ``CancelledError`` and skip
            # the post-await bookkeeping.
            await anyio.sleep(0.1)
            self.close_finished = True
            await super().close()

    ws = _SlowCloseWebSocket()
    client = _FakeClient(ws)
    accessor = _accessor_for_pod(client)

    with anyio.fail_after(5.0):
        with pytest.raises(KubexClientException, match="wall-clock bound"):
            await accessor.run(
                "my-pod",
                command=["sleep", "100"],
                request_timeout=Timeout(total=0.1),
            )

    assert ws.close_finished
    assert ws.closed


@pytest.mark.anyio
async def test_run_unwraps_base_exception_group_from_inner_task() -> None:
    """Regression: ``run()`` spawns ``_drain_*`` and ``_write_stdin`` tasks in
    an inner ``anyio.create_task_group``. anyio 4 wraps a task's exception in
    a ``BaseExceptionGroup`` even when only one task fails, so a transport
    error during stdin write would surface as ``BaseExceptionGroup`` rather
    than the documented ``KubexClientException``. The accessor must unwrap
    single-exception groups so callers ``except KubexClientException`` for
    every exec failure mode."""

    class _SendFailingWebSocket(_FakeWebSocket):
        async def send_bytes(self, data: bytes) -> None:
            raise KubexClientException("transport error")

    ws = _SendFailingWebSocket()
    status_payload = json.dumps(
        {"apiVersion": "v1", "kind": "Status", "metadata": {}, "status": "Success"}
    ).encode()
    ws.feed(bytes([3]) + status_payload)
    ws.feed_eof()

    client = _FakeClient(ws)
    accessor = _accessor_for_pod(client)

    with pytest.raises(KubexClientException, match="transport error"):
        await accessor.run("my-pod", command=["cat"], stdin=b"data")


@pytest.mark.anyio
async def test_run_with_empty_stdin_opens_and_closes_channel() -> None:
    """``run(..., stdin=b"")`` must enable the stdin channel, write zero
    bytes, and close it — distinct from ``stdin=None`` which never opens
    the channel. This pins the ``stdin is not None`` (vs ``if stdin``)
    contract that CLAUDE.md documents."""
    ws = _FakeWebSocket()
    status_payload = json.dumps(
        {"apiVersion": "v1", "kind": "Status", "metadata": {}, "status": "Success"}
    ).encode()
    ws.feed(bytes([3]) + status_payload)
    ws.feed_eof()

    client = _FakeClient(ws)
    accessor = _accessor_for_pod(client)
    result = await accessor.run("my-pod", command=["cat"], stdin=b"")

    assert result.stdout == b""
    request, _ = client.connect_calls[0]
    assert request.query_param_pairs is not None
    assert ("stdin", "true") in request.query_param_pairs
    # Zero-byte stdin frame followed by close stdin.
    assert ws.sent[0] == bytes([0])
    assert bytes([255, 0]) in ws.sent
