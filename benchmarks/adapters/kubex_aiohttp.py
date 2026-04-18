from __future__ import annotations

from typing import ClassVar

from kubex.client.aiohttp import AioHttpClient
from kubex.client.client import BaseClient
from kubex.configuration.configuration import ClientConfiguration

from ._kubex_base import KubexAdapterBase


class KubexAioHttpAdapter(KubexAdapterBase):
    name: ClassVar[str] = "kubex-aiohttp-asyncio"
    runtime: ClassVar[str] = "asyncio"

    async def _build_client(self, config: object) -> BaseClient:
        assert isinstance(config, ClientConfiguration)
        return AioHttpClient(config)
