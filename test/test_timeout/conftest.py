from __future__ import annotations

from typing import Any, AsyncGenerator, Iterable

import pytest

from kubex.client.client import BaseClient
from kubex.configuration import ClientConfiguration
from kubex.core.request import Request
from kubex.core.response import HeadersWrapper, Response


class StubClient(BaseClient):
    """A minimal ``BaseClient`` that records requests and returns canned bytes.

    Used by the ``request_timeout`` flow tests to assert that the value passed
    to an ``Api`` method is attached to the outgoing ``Request``.
    """

    def __init__(
        self,
        configuration: ClientConfiguration | None = None,
        *,
        response_content: bytes = b"{}",
        status_code: int = 200,
        stream_lines: Iterable[str] = (),
    ) -> None:
        self._configuration = configuration or ClientConfiguration(
            url="https://example.invalid",
            insecure_skip_tls_verify=True,
        )
        self._inner_client = object()
        self.requests: list[Request] = []
        self._response_content = response_content
        self._status_code = status_code
        self._stream_lines = list(stream_lines)

    def _create_inner_client(self) -> Any:
        return object()

    async def __aenter__(self) -> "StubClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        return None

    async def request(self, request: Request) -> Response:
        self.requests.append(request)
        return Response(
            content=self._response_content,
            headers=HeadersWrapper({}),
            status_code=self._status_code,
        )

    async def stream_lines(self, request: Request) -> AsyncGenerator[str, None]:
        self.requests.append(request)
        for line in self._stream_lines:
            yield line

    async def close(self) -> None:
        return None

    @property
    def last_request(self) -> Request:
        assert self.requests, "StubClient received no requests"
        return self.requests[-1]


@pytest.fixture
def stub_client() -> StubClient:
    return StubClient()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
