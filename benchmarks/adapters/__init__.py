from __future__ import annotations

from typing import Callable

from .protocol import ClientAdapter, PodSpecLite, StreamSample


def _load_kubex_httpx_asyncio() -> type[ClientAdapter]:
    from .kubex_httpx import KubexHttpxAsyncioAdapter

    return KubexHttpxAsyncioAdapter


def _load_kubex_httpx_trio() -> type[ClientAdapter]:
    from .kubex_httpx import KubexHttpxTrioAdapter

    return KubexHttpxTrioAdapter


def _load_kubex_aiohttp() -> type[ClientAdapter]:
    from .kubex_aiohttp import KubexAioHttpAdapter

    return KubexAioHttpAdapter


def _load_kubex_metadata() -> type[ClientAdapter]:
    from .kubex_metadata import KubexMetadataAdapter

    return KubexMetadataAdapter


def _load_k8s_asyncio() -> type[ClientAdapter]:
    from .k8s_asyncio import K8sAsyncioAdapter

    return K8sAsyncioAdapter


ADAPTER_LOADERS: dict[str, Callable[[], type[ClientAdapter]]] = {
    "kubex-httpx-asyncio": _load_kubex_httpx_asyncio,
    "kubex-httpx-trio": _load_kubex_httpx_trio,
    "kubex-aiohttp-asyncio": _load_kubex_aiohttp,
    "kubex-metadata-httpx-asyncio": _load_kubex_metadata,
    "k8s-asyncio": _load_k8s_asyncio,
}


def load_adapter(name: str) -> type[ClientAdapter]:
    """Lazy-import the adapter class so only one library lands in the process."""
    try:
        loader = ADAPTER_LOADERS[name]
    except KeyError as exc:
        raise ValueError(
            f"Unknown adapter {name!r}. Known: {sorted(ADAPTER_LOADERS)}"
        ) from exc
    return loader()


__all__ = [
    "ADAPTER_LOADERS",
    "ClientAdapter",
    "PodSpecLite",
    "StreamSample",
    "load_adapter",
]
