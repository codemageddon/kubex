"""Closing ``Api.watch``, ``api.metadata.watch`` or ``api.logs.stream`` closes the
line stream they read (and so the HTTP response) before ``aclose()`` returns."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator, AsyncIterator, Callable
from typing import Any

import pytest

from kubex.api import Api
from kubex.core.request import Request
from kubex.k8s.v1_35.core.v1.pod import Pod
from test.stub_client import StubClient

pytestmark = pytest.mark.anyio


def _event(api_version: str, kind: str) -> str:
    metadata = {"name": "a", "namespace": "default"}
    obj = {"apiVersion": api_version, "kind": kind, "metadata": metadata}
    return json.dumps({"type": "ADDED", "object": obj})


_POD_EVENT = _event("v1", "Pod")
_METADATA_EVENT = _event("meta.k8s.io/v1", "PartialObjectMetadata")


class _TrackingClient(StubClient):
    """Streams its lines and records whether the stream was closed."""

    def __init__(self, line: str) -> None:
        super().__init__(stream_lines=[line, line])
        self.closed = False

    async def stream_lines(self, request: Request) -> AsyncGenerator[str, None]:
        self.requests.append(request)
        try:
            for line in self._stream_lines:
                yield line
        finally:
            self.closed = True


Consumer = Callable[[Api[Pod]], AsyncIterator[Any]]

CONSUMERS = [
    pytest.param(lambda api: api.watch(), _POD_EVENT, id="watch"),
    pytest.param(
        lambda api: api.metadata.watch(), _METADATA_EVENT, id="metadata-watch"
    ),
    pytest.param(lambda api: api.logs.stream("a"), "a log line", id="logs-stream"),
]


@pytest.mark.parametrize(("consumer", "line"), CONSUMERS)
async def test_closing_a_consumer_closes_its_line_stream(
    consumer: Consumer, line: str
) -> None:
    client = _TrackingClient(line)
    api: Api[Pod] = Api(Pod, client=client, namespace="default")
    stream = consumer(api)
    assert isinstance(stream, AsyncGenerator)
    await anext(stream)
    assert not client.closed

    await stream.aclose()

    assert client.closed
