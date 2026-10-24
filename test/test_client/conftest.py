from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import pytest

from kubex.client.client import BaseClient
from kubex.client.options import ClientOptions
from kubex.configuration import ClientConfiguration


@dataclass(frozen=True)
class BackendCase:
    client: str
    runtime: str


ClientFactory = Callable[..., BaseClient]


@pytest.fixture(
    params=[
        BackendCase("aiohttp", "asyncio"),
        BackendCase("httpx", "asyncio"),
        BackendCase("httpx", "trio"),
    ],
    ids=lambda case: f"{case.client}-{case.runtime}",
)
def backend_case(request: pytest.FixtureRequest) -> BackendCase:
    """Every supported client/runtime pair (aiohttp is asyncio-only).

    Modules opting in define ``anyio_backend`` as ``backend_case.runtime``.
    """
    case: BackendCase = request.param
    return case


@pytest.fixture
def make_client(backend_case: BackendCase) -> ClientFactory:
    def _make(
        url: str, options: ClientOptions | None = None, **config: Any
    ) -> BaseClient:
        configuration = ClientConfiguration(url=url, **config)
        if backend_case.client == "aiohttp":
            from kubex.client.aiohttp import AioHttpClient

            return AioHttpClient(configuration, options)
        from kubex.client.httpx import HttpxClient

        return HttpxClient(configuration, options)

    return _make
