from __future__ import annotations

from typing import Any, Sequence

import anyio
import pytest

from kubex.client.client import BaseClient
from kubex.client.websocket import WebSocketConnection
from kubex.core.exceptions import KubexClientException
from kubex.core.exec_channels import V4ChannelProtocol
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
        subprotocol: str | None = "v4.channel.k8s.io",
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
        raise AssertionError("request should not be called for portforward")

    def stream_lines(self, request: Request) -> Any:  # pragma: no cover
        raise AssertionError("stream_lines should not be called for portforward")

    async def close(self) -> None:
        return None

    async def connect_websocket(
        self, request: Request, subprotocols: Sequence[str]
    ) -> WebSocketConnection:
        self.connect_calls.append((request, list(subprotocols)))
        return self._websocket


def _accessor_for_pod(client: BaseClient) -> Any:
    from kubex.api._portforward import PortforwardAccessor

    builder = RequestBuilder(resource_config=Pod.__RESOURCE_CONFIG__)
    return PortforwardAccessor(
        client=client,
        request_builder=builder,
        namespace="default",
        scope=Scope.NAMESPACE,
        resource_type=Pod,
    )


def _make_port_prefix(port: int) -> bytes:
    return port.to_bytes(2, byteorder="little")


@pytest.mark.anyio
async def test_forward_opens_websocket_with_portforward_url_and_v4_subprotocol() -> (
    None
):
    ws = _FakeWebSocket()
    ws.feed_eof()
    client = _FakeClient(ws)
    accessor = _accessor_for_pod(client)

    async with accessor.forward("my-pod", ports=[8080]):
        pass

    assert len(client.connect_calls) == 1
    request, subprotocols = client.connect_calls[0]
    assert request.method == "GET"
    assert request.url.endswith("/pods/my-pod/portforward")
    assert "namespaces/default" in request.url
    # Kubelet's portforward WebSocket only registers v4 subprotocols; v5
    # (which adds CHANNEL_CLOSE) is rejected with 403.
    assert subprotocols == [V4ChannelProtocol.subprotocol]


@pytest.mark.anyio
async def test_forward_passes_ports_as_repeated_query_param_pairs() -> None:
    ws = _FakeWebSocket()
    ws.feed_eof()
    client = _FakeClient(ws)
    accessor = _accessor_for_pod(client)

    async with accessor.forward("my-pod", ports=[8080, 9090]):
        pass

    request, _ = client.connect_calls[0]
    assert request.query_param_pairs is not None
    pairs = request.query_param_pairs
    assert ("ports", "8080") in pairs
    assert ("ports", "9090") in pairs
    assert request.query_params is None


@pytest.mark.anyio
async def test_forward_yields_port_forwarder_with_streams_and_errors() -> None:
    from kubex.api._portforward import PortForwarder, PortForwardStream

    ws = _FakeWebSocket()
    # Feed port-prefix frames for each channel so the session read loop can
    # validate them and close cleanly.
    ws.feed(bytes([0]) + _make_port_prefix(8080))  # data channel 0, port 8080
    ws.feed(bytes([1]) + _make_port_prefix(8080))  # error channel 1, port 8080
    ws.feed_eof()

    client = _FakeClient(ws)
    accessor = _accessor_for_pod(client)

    async with accessor.forward("my-pod", ports=[8080]) as pf:
        assert isinstance(pf, PortForwarder)
        assert 8080 in pf.streams
        assert 8080 in pf.errors
        assert isinstance(pf.streams[8080], PortForwardStream)


@pytest.mark.anyio
async def test_forward_yields_port_forwarder_with_multiple_ports() -> None:
    from kubex.api._portforward import PortForwarder

    ws = _FakeWebSocket()
    ws.feed(bytes([0]) + _make_port_prefix(8080))
    ws.feed(bytes([1]) + _make_port_prefix(8080))
    ws.feed(bytes([2]) + _make_port_prefix(9090))
    ws.feed(bytes([3]) + _make_port_prefix(9090))
    ws.feed_eof()

    client = _FakeClient(ws)
    accessor = _accessor_for_pod(client)

    async with accessor.forward("my-pod", ports=[8080, 9090]) as pf:
        assert isinstance(pf, PortForwarder)
        assert set(pf.streams.keys()) == {8080, 9090}
        assert set(pf.errors.keys()) == {8080, 9090}


@pytest.mark.anyio
async def test_forward_port_data_truncated_is_live_view() -> None:
    from kubex.api._portforward import PortForwarder

    ws = _FakeWebSocket()
    ws.feed_eof()

    client = _FakeClient(ws)
    accessor = _accessor_for_pod(client)

    async with accessor.forward("my-pod", ports=[8080]) as pf:
        assert isinstance(pf, PortForwarder)
        assert pf.port_data_truncated[8080] is False
        # Simulate a buffer overflow so we can verify the property is a live
        # view of the underlying session state, not a snapshot.
        pf._session._truncated[8080] = True
        assert pf.port_data_truncated[8080] is True


@pytest.mark.anyio
async def test_forward_closes_websocket_on_exit() -> None:
    ws = _FakeWebSocket()
    ws.feed_eof()
    client = _FakeClient(ws)
    accessor = _accessor_for_pod(client)

    async with accessor.forward("my-pod", ports=[8080]):
        assert not ws.closed
    assert ws.closed


@pytest.mark.anyio
async def test_forward_closes_websocket_on_exception() -> None:
    ws = _FakeWebSocket()
    ws.feed_eof()
    client = _FakeClient(ws)
    accessor = _accessor_for_pod(client)

    with pytest.raises(RuntimeError, match="boom"):
        async with accessor.forward("my-pod", ports=[8080]):
            raise RuntimeError("boom")
    assert ws.closed


@pytest.mark.anyio
async def test_forward_raises_kubex_client_exception_for_unsupported_subprotocol() -> (
    None
):
    ws = _FakeWebSocket(subprotocol="unknown.protocol.k8s.io")
    ws.feed_eof()
    client = _FakeClient(ws)
    accessor = _accessor_for_pod(client)

    with pytest.raises(KubexClientException, match="unsupported subprotocol"):
        async with accessor.forward("my-pod", ports=[8080]):
            pass

    assert ws.closed


@pytest.mark.anyio
async def test_forward_handshake_failure_propagates() -> None:
    class _FailingClient(_FakeClient):
        async def connect_websocket(
            self, request: Request, subprotocols: Sequence[str]
        ) -> WebSocketConnection:
            raise KubexClientException("handshake failed")

    ws = _FakeWebSocket()
    client = _FailingClient(ws)
    accessor = _accessor_for_pod(client)

    with pytest.raises(KubexClientException, match="handshake failed"):
        async with accessor.forward("my-pod", ports=[8080]):
            pass


def test_descriptor_returns_portforward_accessor_for_pod() -> None:
    from kubex.api._portforward import PortforwardAccessor
    from kubex.api.api import Api

    client = StubClient()
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    accessor = api.portforward
    assert isinstance(accessor, PortforwardAccessor)


def test_descriptor_raises_not_implemented_for_namespace() -> None:
    from kubex.api.api import Api

    client = StubClient()
    api: Api[Namespace] = Api(Namespace, client=client)
    with pytest.raises(NotImplementedError, match="PortForward is only supported"):
        _ = api.portforward


def test_descriptor_caches_accessor_on_instance() -> None:
    from kubex.api.api import Api

    client = StubClient()
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    assert api.portforward is api.portforward
