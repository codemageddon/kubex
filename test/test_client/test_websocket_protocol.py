from __future__ import annotations

from collections import deque
from typing import Any, AsyncGenerator

import pytest

from kubex.client.client import BaseClient
from kubex.client.websocket import WebSocketConnection
from kubex.configuration import ClientConfiguration
from kubex.core.request import Request
from kubex.core.response import Response


class FakeWebSocketConnection(WebSocketConnection):
    """In-memory WebSocketConnection used to validate the protocol shape."""

    def __init__(
        self,
        *,
        incoming: list[bytes] | None = None,
        negotiated_subprotocol: str | None = "v5.channel.k8s.io",
    ) -> None:
        self._incoming: deque[bytes] = deque(incoming or [])
        self.sent: list[bytes] = []
        self._closed = False
        self._negotiated_subprotocol = negotiated_subprotocol

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def negotiated_subprotocol(self) -> str | None:
        return self._negotiated_subprotocol

    async def send_bytes(self, data: bytes) -> None:
        if self._closed:
            raise RuntimeError("send_bytes on closed connection")
        self.sent.append(data)

    async def receive_bytes(self) -> bytes:
        if self._closed:
            raise RuntimeError("receive_bytes on closed connection")
        if not self._incoming:
            self._closed = True
            raise StopAsyncIteration
        return self._incoming.popleft()

    async def close(self) -> None:
        self._closed = True


def test_fake_websocket_connection_is_websocket_connection() -> None:
    conn = FakeWebSocketConnection()
    assert isinstance(conn, WebSocketConnection)


def test_websocket_connection_is_abstract() -> None:
    with pytest.raises(TypeError):
        WebSocketConnection()  # type: ignore[abstract]


@pytest.mark.anyio
async def test_fake_websocket_connection_send_bytes_records_payload() -> None:
    conn = FakeWebSocketConnection()
    await conn.send_bytes(b"\x00hello")
    assert conn.sent == [b"\x00hello"]


@pytest.mark.anyio
async def test_fake_websocket_connection_receive_bytes_returns_queued_frame() -> None:
    conn = FakeWebSocketConnection(incoming=[b"\x01out", b"\x02err"])
    assert await conn.receive_bytes() == b"\x01out"
    assert await conn.receive_bytes() == b"\x02err"


@pytest.mark.anyio
async def test_fake_websocket_connection_close_sets_closed_true() -> None:
    conn = FakeWebSocketConnection()
    assert conn.closed is False
    await conn.close()
    assert conn.closed is True


def test_websocket_connection_negotiated_subprotocol_property() -> None:
    conn = FakeWebSocketConnection(negotiated_subprotocol="v5.channel.k8s.io")
    assert conn.negotiated_subprotocol == "v5.channel.k8s.io"


def test_websocket_connection_negotiated_subprotocol_can_be_none() -> None:
    conn = FakeWebSocketConnection(negotiated_subprotocol=None)
    assert conn.negotiated_subprotocol is None


@pytest.mark.anyio
async def test_websocket_connection_works_as_async_context_manager() -> None:
    conn = FakeWebSocketConnection()
    async with conn as entered:
        assert entered is conn
        assert conn.closed is False
    assert conn.closed is True


@pytest.mark.anyio
async def test_websocket_connection_async_context_manager_closes_on_exception() -> None:
    conn = FakeWebSocketConnection()
    with pytest.raises(RuntimeError, match="boom"):
        async with conn:
            raise RuntimeError("boom")
    assert conn.closed is True


class _MinimalClient(BaseClient):
    """Concrete BaseClient that does not override connect_websocket."""

    def __init__(self) -> None:
        self._configuration = ClientConfiguration(
            url="https://example.invalid",
            insecure_skip_tls_verify=True,
        )
        self._inner_client = object()

    def _create_inner_client(self) -> Any:
        return object()

    async def request(self, request: Request) -> Response:
        raise NotImplementedError

    async def stream_lines(self, request: Request) -> AsyncGenerator[str, None]:
        if False:
            yield ""
        raise NotImplementedError

    async def close(self) -> None:
        return None


@pytest.mark.anyio
async def test_base_client_connect_websocket_default_raises_clear_error() -> None:
    client = _MinimalClient()
    request = Request(method="GET", url="/api/v1/namespaces/default/pods/p/exec")
    with pytest.raises(NotImplementedError, match="WebSocket"):
        await client.connect_websocket(request, ["v5.channel.k8s.io"])
