from __future__ import annotations

from typing import ClassVar

from kubex.client.client import BaseClient
from kubex.client.httpx import HttpxClient
from kubex.configuration.configuration import ClientConfiguration

from ._kubex_base import KubexAdapterBase


class KubexHttpxAsyncioAdapter(KubexAdapterBase):
    name: ClassVar[str] = "kubex-httpx-asyncio"
    runtime: ClassVar[str] = "asyncio"

    async def _build_client(self, config: object) -> BaseClient:
        assert isinstance(config, ClientConfiguration)
        return HttpxClient(config)


class KubexHttpxTrioAdapter(KubexAdapterBase):
    name: ClassVar[str] = "kubex-httpx-trio"
    runtime: ClassVar[str] = "trio"

    async def _build_client(self, config: object) -> BaseClient:
        assert isinstance(config, ClientConfiguration)
        return HttpxClient(config)
