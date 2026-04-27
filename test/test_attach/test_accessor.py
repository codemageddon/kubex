from __future__ import annotations

from typing import Any, Sequence

import anyio
import pytest

from kubex.client.client import BaseClient
from kubex.client.websocket import WebSocketConnection
from kubex.core.exceptions import KubexClientException
from kubex.core.exec_channels import V5ChannelProtocol
from kubex.core.request import Request
from kubex.core.request_builder.builder import RequestBuilder
from kubex.k8s.v1_35.core.v1.namespace import Namespace
from kubex.k8s.v1_35.core.v1.pod import Pod
from kubex_core.models.resource_config import Scope
from test.stub_client import StubClient


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

    def _create_inner_client(self) -> Any:  # pragma: no cover
        return object()

    async def request(self, request: Request) -> Any:  # pragma: no cover
        raise AssertionError("request should not be called for attach")

    def stream_lines(self, request: Request) -> Any:  # pragma: no cover
        raise AssertionError("stream_lines should not be called for attach")

    async def close(self) -> None:
        return None

    async def connect_websocket(
        self, request: Request, subprotocols: Sequence[str]
    ) -> WebSocketConnection:
        self.connect_calls.append((request, list(subprotocols)))
        return self._websocket


def _accessor_for_pod(client: BaseClient) -> Any:
    from kubex.api._attach import AttachAccessor

    builder = RequestBuilder(resource_config=Pod.__RESOURCE_CONFIG__)
    return AttachAccessor(
        client=client,
        request_builder=builder,
        namespace="default",
        scope=Scope.NAMESPACE,
        resource_type=Pod,
    )


@pytest.mark.anyio
async def test_stream_opens_websocket_with_attach_url_and_v5_subprotocol() -> None:
    ws = _FakeWebSocket()
    ws.feed_eof()
    client = _FakeClient(ws)
    accessor = _accessor_for_pod(client)

    async with accessor.stream("my-pod") as session:
        assert session is not None

    assert len(client.connect_calls) == 1
    request, subprotocols = client.connect_calls[0]
    assert request.method == "GET"
    assert request.url.endswith("/pods/my-pod/attach")
    assert "namespaces/default" in request.url
    assert subprotocols == [V5ChannelProtocol.subprotocol]


@pytest.mark.anyio
async def test_stream_passes_options_to_request() -> None:
    ws = _FakeWebSocket()
    ws.feed_eof()
    client = _FakeClient(ws)
    accessor = _accessor_for_pod(client)

    async with accessor.stream(
        "my-pod",
        container="app",
        stdin=True,
        tty=True,
    ):
        pass

    request, _ = client.connect_calls[0]
    assert request.query_param_pairs is not None
    pairs = request.query_param_pairs
    assert ("container", "app") in pairs
    assert ("stdin", "true") in pairs
    assert ("tty", "true") in pairs
    assert ("stdout", "true") in pairs
    assert ("stderr", "true") in pairs
    # attach has no command param
    assert all(k != "command" for k, _ in pairs)


@pytest.mark.anyio
async def test_stream_yields_stream_session() -> None:
    from kubex.api._stream_session import StreamSession

    ws = _FakeWebSocket()
    ws.feed_eof()
    client = _FakeClient(ws)
    accessor = _accessor_for_pod(client)

    async with accessor.stream("my-pod") as session:
        assert isinstance(session, StreamSession)


@pytest.mark.anyio
async def test_stream_closes_websocket_on_exit() -> None:
    ws = _FakeWebSocket()
    ws.feed_eof()
    client = _FakeClient(ws)
    accessor = _accessor_for_pod(client)

    async with accessor.stream("my-pod"):
        assert not ws.closed
    assert ws.closed


@pytest.mark.anyio
async def test_stream_closes_websocket_on_exception() -> None:
    ws = _FakeWebSocket()
    ws.feed_eof()
    client = _FakeClient(ws)
    accessor = _accessor_for_pod(client)

    with pytest.raises(RuntimeError, match="boom"):
        async with accessor.stream("my-pod"):
            raise RuntimeError("boom")
    assert ws.closed


@pytest.mark.anyio
async def test_stream_raises_kubex_client_exception_for_unsupported_subprotocol() -> (
    None
):
    ws = _FakeWebSocket(subprotocol="unknown.protocol.k8s.io")
    ws.feed_eof()
    client = _FakeClient(ws)
    accessor = _accessor_for_pod(client)

    with pytest.raises(KubexClientException, match="unsupported subprotocol"):
        async with accessor.stream("my-pod"):
            pass

    assert ws.closed


def test_descriptor_returns_attach_accessor_for_pod() -> None:
    from kubex.api._attach import AttachAccessor
    from kubex.api.api import Api

    client = StubClient()
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    accessor = api.attach
    assert isinstance(accessor, AttachAccessor)


def test_descriptor_raises_not_implemented_for_namespace() -> None:
    from kubex.api.api import Api

    client = StubClient()
    api: Api[Namespace] = Api(Namespace, client=client)
    with pytest.raises(NotImplementedError, match="Attach is only supported"):
        _ = api.attach


def test_descriptor_caches_accessor_on_instance() -> None:
    from kubex.api.api import Api

    client = StubClient()
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    assert api.attach is api.attach


@pytest.mark.anyio
async def test_stream_handshake_failure_closes_connection() -> None:
    """When connect_websocket raises, the exception propagates without leaking."""

    class _FailingClient(_FakeClient):
        async def connect_websocket(
            self, request: Request, subprotocols: Sequence[str]
        ) -> WebSocketConnection:
            raise KubexClientException("handshake failed")

    ws = _FakeWebSocket()
    client = _FailingClient(ws)
    accessor = _accessor_for_pod(client)

    with pytest.raises(KubexClientException, match="handshake failed"):
        async with accessor.stream("my-pod"):
            pass
