from __future__ import annotations

from typing import ClassVar

from kubex.client.aiohttp import AioHttpClient
from kubex.client.client import BaseClient
from kubex.configuration.configuration import ClientConfiguration

from ._kubex_base import KubexAdapterBase
from .protocol import (
    CAP_METADATA,
    CAP_NAMESPACE_LIST,
    CAP_POD_CRUD,
    PodSpecLite,
    StreamSample,
)


class KubexMetadataAdapter(KubexAdapterBase):
    """Uses kubex's PartialObjectMetadata API for list/get.

    Exists to measure the wire + modeling savings of `?as=PartialObjectMetadata`
    vs. full-object deserialization. Creation/deletion still route through the
    typed Pod API because those endpoints have no metadata-only equivalent.
    """

    name: ClassVar[str] = "kubex-metadata-aiohttp-asyncio"
    capabilities: ClassVar[frozenset[str]] = frozenset(
        {CAP_POD_CRUD, CAP_NAMESPACE_LIST, CAP_METADATA}
    )
    runtime: ClassVar[str] = "asyncio"

    async def _build_client(self, config: object) -> BaseClient:
        assert isinstance(config, ClientConfiguration)
        return AioHttpClient(config)

    async def list_pods(self, namespace: str, *, limit: int | None = None) -> int:
        result = await self._pods().metadata.list(namespace=namespace, limit=limit)
        return len(result.items or [])

    async def get_pod(self, namespace: str, name: str) -> None:
        await self._pods().metadata.get(name, namespace=namespace)

    async def create_pod(self, namespace: str, spec: PodSpecLite) -> None:
        raise NotImplementedError(
            "metadata-only adapter does not implement create (asymmetric scenario)"
        )

    async def delete_pod(self, namespace: str, name: str) -> None:
        raise NotImplementedError(
            "metadata-only adapter does not implement delete (asymmetric scenario)"
        )

    async def watch_pods(self, namespace: str, n_events: int) -> StreamSample:
        raise NotImplementedError("metadata-only adapter: watch out of scope")

    async def stream_logs(
        self, namespace: str, name: str, n_lines: int
    ) -> StreamSample:
        raise NotImplementedError("metadata-only adapter: logs out of scope")
