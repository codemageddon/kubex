from __future__ import annotations

import logging
import socket
from collections.abc import Callable
from typing import Any, Sequence

import anyio
import anyio.abc
import pytest

from kubex.api._portforward import PortforwardAccessor
from kubex.client.client import BaseClient
from kubex.client.websocket import WebSocketConnection
from kubex.configuration import ClientConfiguration
from kubex.core.exec_channels import CHANNEL_CLOSE
from kubex.core.request import Request
from kubex.core.request_builder.builder import RequestBuilder
from kubex.k8s.v1_35.core.v1.pod import Pod
from kubex_core.models.resource_config import Scope


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        host, port = s.getsockname()
        return int(port)


def _port_prefix(port: int) -> bytes:
    return port.to_bytes(2, byteorder="little")


class _FakeWebSocket(WebSocketConnection):
    def __init__(self, *, buffer: int = 256) -> None:
        self.sent: list[bytes] = []
        self._send, self._recv = anyio.create_memory_object_stream[bytes](
            max_buffer_size=buffer
        )
        self._closed = False

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def negotiated_subprotocol(self) -> str | None:
        return "v4.channel.k8s.io"

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


class _DynamicFakeClient(BaseClient):
    """Stub client that creates a new WebSocket via factory on each connect."""

    def __init__(self, ws_factory: Callable[[], _FakeWebSocket]) -> None:
        super().__init__(
            ClientConfiguration(
                url="https://example.invalid", insecure_skip_tls_verify=True
            )
        )
        self._ws_factory = ws_factory
        self.connect_count = 0

    def _create_inner_client(self) -> Any:
        return object()

    async def request(self, request: Request) -> Any:  # pragma: no cover
        raise AssertionError("request should not be called")

    def stream_lines(self, request: Request) -> Any:  # pragma: no cover
        raise AssertionError("stream_lines should not be called")

    async def close(self) -> None:
        pass

    async def connect_websocket(
        self, request: Request, subprotocols: Sequence[str]
    ) -> WebSocketConnection:
        self.connect_count += 1
        return self._ws_factory()


def _accessor_for_pod(client: BaseClient) -> PortforwardAccessor[Pod]:
    builder = RequestBuilder(resource_config=Pod.__RESOURCE_CONFIG__)
    return PortforwardAccessor(
        client=client,
        request_builder=builder,
        namespace="default",
        scope=Scope.NAMESPACE,
        resource_type=Pod,
    )


@pytest.mark.anyio
async def test_listen_opens_tcp_listener_on_specified_port() -> None:
    local_port = _get_free_port()
    ws_ready = anyio.Event()

    def ws_factory() -> _FakeWebSocket:
        ws = _FakeWebSocket()
        ws.feed_eof()
        ws_ready.set()
        return ws

    accessor = _accessor_for_pod(_DynamicFakeClient(ws_factory))

    async with accessor.listen("my-pod", port_map={80: local_port}):
        async with await anyio.connect_tcp("127.0.0.1", local_port):
            pass  # connection succeeded


@pytest.mark.anyio
async def test_accepting_connection_opens_fresh_session_per_connection() -> None:
    local_port = _get_free_port()
    ws_list: list[_FakeWebSocket] = []
    events = [anyio.Event(), anyio.Event()]
    idx = 0

    def ws_factory() -> _FakeWebSocket:
        nonlocal idx
        ws = _FakeWebSocket()
        ws.feed_eof()
        ws_list.append(ws)
        events[idx].set()
        idx += 1
        return ws

    client = _DynamicFakeClient(ws_factory)
    accessor = _accessor_for_pod(client)

    async with accessor.listen("my-pod", port_map={80: local_port}):
        async with await anyio.connect_tcp("127.0.0.1", local_port):
            await events[0].wait()

        async with await anyio.connect_tcp("127.0.0.1", local_port):
            await events[1].wait()

    assert client.connect_count == 2


@pytest.mark.anyio
async def test_local_bytes_forwarded_to_remote_frames() -> None:
    local_port = _get_free_port()
    ws_list: list[_FakeWebSocket] = []
    ws_ready = anyio.Event()

    def ws_factory() -> _FakeWebSocket:
        ws = _FakeWebSocket(buffer=256)
        # Pre-feed port-prefix frames so the session read loop validates them.
        ws.feed(bytes([0]) + _port_prefix(80))  # data channel 0
        ws.feed(bytes([1]) + _port_prefix(80))  # error channel 1
        ws_list.append(ws)
        ws_ready.set()
        return ws

    accessor = _accessor_for_pod(_DynamicFakeClient(ws_factory))

    async with accessor.listen("my-pod", port_map={80: local_port}):
        async with await anyio.connect_tcp("127.0.0.1", local_port) as sock:
            await ws_ready.wait()
            ws = ws_list[0]

            await sock.send(b"GET / HTTP/1.0\r\n\r\n")
            # Give copy task time to forward the bytes.
            await anyio.sleep(0.05)

            data_channel_frame = bytes([0]) + b"GET / HTTP/1.0\r\n\r\n"
            assert data_channel_frame in ws.sent


@pytest.mark.anyio
async def test_remote_data_forwarded_to_local_socket() -> None:
    local_port = _get_free_port()
    ws_list: list[_FakeWebSocket] = []
    ws_ready = anyio.Event()

    def ws_factory() -> _FakeWebSocket:
        ws = _FakeWebSocket(buffer=256)
        ws.feed(bytes([0]) + _port_prefix(80))  # data channel port-prefix
        ws.feed(bytes([1]) + _port_prefix(80))  # error channel port-prefix
        ws_list.append(ws)
        ws_ready.set()
        return ws

    accessor = _accessor_for_pod(_DynamicFakeClient(ws_factory))

    async with accessor.listen("my-pod", port_map={80: local_port}):
        async with await anyio.connect_tcp("127.0.0.1", local_port) as sock:
            await ws_ready.wait()
            ws = ws_list[0]

            # Feed a data frame from the remote side (no prefix, after first frame).
            ws.feed(bytes([0]) + b"HTTP/1.0 200 OK\r\n\r\n")

            with anyio.fail_after(2.0):
                data = await sock.receive()
            assert data == b"HTTP/1.0 200 OK\r\n\r\n"


@pytest.mark.anyio
async def test_closing_local_socket_does_not_send_close_frame_on_v4() -> None:
    # The v4 portforward subprotocol does not support CHANNEL_CLOSE — the
    # kubelet would silently drop a frame addressed to channel id 255 on v4.
    # The session marks the channel half-closed locally and relies on the
    # kubelet seeing TCP EOF on the pod side (via WebSocket close on session
    # exit) for full teardown.
    local_port = _get_free_port()
    ws_list: list[_FakeWebSocket] = []
    ws_ready = anyio.Event()

    def ws_factory() -> _FakeWebSocket:
        ws = _FakeWebSocket(buffer=256)
        ws.feed(bytes([0]) + _port_prefix(80))
        ws.feed(bytes([1]) + _port_prefix(80))
        ws_list.append(ws)
        ws_ready.set()
        return ws

    accessor = _accessor_for_pod(_DynamicFakeClient(ws_factory))

    async with accessor.listen("my-pod", port_map={80: local_port}):
        sock = await anyio.connect_tcp("127.0.0.1", local_port)
        await ws_ready.wait()
        ws = ws_list[0]

        await sock.aclose()
        await anyio.sleep(0.05)

        assert bytes([CHANNEL_CLOSE, 0]) not in ws.sent


@pytest.mark.anyio
async def test_context_exit_closes_listener() -> None:
    local_port = _get_free_port()

    def ws_factory() -> _FakeWebSocket:
        ws = _FakeWebSocket()
        ws.feed_eof()
        return ws

    accessor = _accessor_for_pod(_DynamicFakeClient(ws_factory))

    async with accessor.listen("my-pod", port_map={80: local_port}):
        # Listener is active inside the context.
        async with await anyio.connect_tcp("127.0.0.1", local_port):
            pass

    # After context exit the listener must be closed; connecting must fail.
    with pytest.raises(OSError):
        await anyio.connect_tcp("127.0.0.1", local_port)


@pytest.mark.anyio
async def test_error_frames_are_logged(caplog: pytest.LogCaptureFixture) -> None:
    local_port = _get_free_port()
    ws_list: list[_FakeWebSocket] = []
    ws_ready = anyio.Event()

    def ws_factory() -> _FakeWebSocket:
        ws = _FakeWebSocket(buffer=256)
        ws.feed(bytes([0]) + _port_prefix(80))
        ws.feed(bytes([1]) + _port_prefix(80))
        ws_list.append(ws)
        ws_ready.set()
        return ws

    accessor = _accessor_for_pod(_DynamicFakeClient(ws_factory))

    with caplog.at_level(logging.WARNING, logger="kubex.portforward"):
        async with accessor.listen("my-pod", port_map={80: local_port}):
            async with await anyio.connect_tcp("127.0.0.1", local_port):
                await ws_ready.wait()
                ws = ws_list[0]

                # Feed an error frame: error channel 1 with error text.
                error_text = b"connection refused"
                ws.feed(bytes([1]) + error_text)
                ws.feed_eof()

                await anyio.sleep(0.05)

    assert any(
        "80" in r.message and "connection refused" in r.message for r in caplog.records
    )


@pytest.mark.anyio
async def test_multiple_port_map_entries_open_independent_listeners() -> None:
    port_80 = _get_free_port()
    port_443 = _get_free_port()
    ws_list: list[_FakeWebSocket] = []
    events: dict[int, anyio.Event] = {80: anyio.Event(), 443: anyio.Event()}

    def ws_factory() -> _FakeWebSocket:
        ws = _FakeWebSocket()
        ws.feed_eof()
        ws_list.append(ws)
        return ws

    client = _DynamicFakeClient(ws_factory)
    accessor = _accessor_for_pod(client)

    async with accessor.listen("my-pod", port_map={80: port_80, 443: port_443}):
        async with await anyio.connect_tcp("127.0.0.1", port_80):
            events[80].set()
        async with await anyio.connect_tcp("127.0.0.1", port_443):
            events[443].set()

    assert events[80].is_set()
    assert events[443].is_set()
    assert client.connect_count == 2


@pytest.mark.anyio
async def test_listen_rejects_empty_port_map() -> None:
    accessor = _accessor_for_pod(_DynamicFakeClient(lambda: _FakeWebSocket()))
    with pytest.raises(ValueError, match="at least one entry"):
        async with accessor.listen("my-pod", port_map={}):
            pass


@pytest.mark.anyio
async def test_listen_rejects_duplicate_local_ports() -> None:
    local_port = _get_free_port()
    accessor = _accessor_for_pod(_DynamicFakeClient(lambda: _FakeWebSocket()))
    with pytest.raises(ValueError, match="duplicate local ports"):
        async with accessor.listen(
            "my-pod", port_map={80: local_port, 443: local_port}
        ):
            pass


@pytest.mark.anyio
async def test_listen_rejects_remote_port_out_of_range() -> None:
    accessor = _accessor_for_pod(_DynamicFakeClient(lambda: _FakeWebSocket()))
    with pytest.raises(ValueError, match="out of range"):
        async with accessor.listen("my-pod", port_map={70000: 18080}):
            pass


@pytest.mark.anyio
async def test_listen_rejects_remote_port_zero() -> None:
    accessor = _accessor_for_pod(_DynamicFakeClient(lambda: _FakeWebSocket()))
    with pytest.raises(ValueError, match="out of range"):
        async with accessor.listen("my-pod", port_map={0: 18080}):
            pass


@pytest.mark.anyio
async def test_listen_rejects_non_int_remote_port() -> None:
    accessor = _accessor_for_pod(_DynamicFakeClient(lambda: _FakeWebSocket()))
    with pytest.raises(TypeError, match="remote port must be int"):
        async with accessor.listen("my-pod", port_map={True: 18080}):
            pass


@pytest.mark.anyio
async def test_local_half_close_does_not_drop_remote_response() -> None:
    """A TCP client that half-closes its write side must still receive the
    remote response — copy() must propagate EOF as a half-close, not full
    close, so the response path remains open."""
    local_port = _get_free_port()
    ws_list: list[_FakeWebSocket] = []
    ws_ready = anyio.Event()

    def ws_factory() -> _FakeWebSocket:
        ws = _FakeWebSocket(buffer=256)
        ws.feed(bytes([0]) + _port_prefix(80))  # data channel port-prefix
        ws.feed(bytes([1]) + _port_prefix(80))  # error channel port-prefix
        ws_list.append(ws)
        ws_ready.set()
        return ws

    accessor = _accessor_for_pod(_DynamicFakeClient(ws_factory))

    async with accessor.listen("my-pod", port_map={80: local_port}):
        async with await anyio.connect_tcp("127.0.0.1", local_port) as sock:
            await ws_ready.wait()
            ws = ws_list[0]

            # Write request, half-close write side, then expect a response.
            await sock.send(b"GET / HTTP/1.0\r\n\r\n")
            await sock.send_eof()

            # Simulate kubelet sending a response after seeing client EOF.
            await anyio.sleep(0.05)
            ws.feed(bytes([0]) + b"HTTP/1.0 200 OK\r\n\r\nbody")
            ws.feed_eof()

            with anyio.fail_after(2.0):
                received = b""
                while True:
                    try:
                        chunk = await sock.receive()
                    except anyio.EndOfStream:
                        break
                    received += chunk
            assert b"HTTP/1.0 200 OK" in received
            assert b"body" in received


@pytest.mark.anyio
async def test_listen_applies_backpressure_without_data_loss(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A slow local TCP reader must not cause data loss.

    The read loop now blocks (awaits) when the per-port memory buffer is full
    instead of closing the stream and dropping bytes.  Closing the local socket
    while the read loop is stalled should unblock it cleanly with no truncation
    warning logged.
    """
    local_port = _get_free_port()
    ws_ready = anyio.Event()

    def ws_factory() -> _FakeWebSocket:
        ws = _FakeWebSocket(buffer=4096)
        ws.feed(bytes([0]) + _port_prefix(80))
        ws.feed(bytes([1]) + _port_prefix(80))
        # Feed frames that will stall the read loop via backpressure.
        for _ in range(200):
            ws.feed(bytes([0]) + b"X" * 64)
        ws_ready.set()
        return ws

    accessor = PortforwardAccessor(
        client=_DynamicFakeClient(ws_factory),
        request_builder=RequestBuilder(resource_config=Pod.__RESOURCE_CONFIG__),
        namespace="default",
        scope=Scope.NAMESPACE,
        resource_type=Pod,
    )

    # Tiny per-port buffer so backpressure kicks in quickly.
    original_open = accessor._open_session

    async def _open_with_tiny_buffer(*args: Any, **kwargs: Any) -> Any:
        kwargs["buffer_size"] = 1
        return await original_open(*args, **kwargs)

    accessor._open_session = _open_with_tiny_buffer  # type: ignore[method-assign]

    with caplog.at_level(logging.WARNING, logger="kubex.portforward"):
        async with accessor.listen("my-pod", port_map={80: local_port}):
            sock = await anyio.connect_tcp("127.0.0.1", local_port)
            await ws_ready.wait()
            try:
                # Don't read — let the read loop stall under backpressure.
                await anyio.sleep(0.1)
            finally:
                await sock.aclose()
            await anyio.sleep(0.1)

    # Backpressure must not produce a "data dropped" warning — data is stalled,
    # not silently discarded.
    assert not any("data dropped" in r.message for r in caplog.records)
