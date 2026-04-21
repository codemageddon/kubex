from __future__ import annotations

import pytest

from kubex.configuration import ClientConfiguration
from kubex.core.params import Timeout

aiohttp = pytest.importorskip("aiohttp")

from kubex.client.aiohttp import AioHttpClient, _to_aiohttp_timeout  # noqa: E402


def _configuration(**kwargs: object) -> ClientConfiguration:
    # Leave ``insecure_skip_tls_verify`` unset so the aiohttp connector builds a
    # valid ``SSLContext`` (the code path would otherwise combine
    # ``verify_ssl=False`` with an ``ssl`` context and raise).
    return ClientConfiguration(
        url="https://example.invalid",
        **kwargs,  # type: ignore[arg-type]
    )


@pytest.mark.anyio
async def test_create_inner_session_with_timeout() -> None:
    client = AioHttpClient(_configuration(timeout=5))
    try:
        assert client._inner_client.timeout.total == 5
    finally:
        await client.close()


@pytest.mark.anyio
async def test_create_inner_session_with_none_disables_timeout() -> None:
    client = AioHttpClient(_configuration(timeout=None))
    try:
        assert client._inner_client.timeout.total is None
    finally:
        await client.close()


def test_to_aiohttp_timeout_maps_read_to_sock_read() -> None:
    translated = _to_aiohttp_timeout(
        Timeout(total=5, connect=1, read=2, write=3, pool=4)
    )
    assert translated.total == 5
    assert translated.sock_connect == 1
    assert translated.sock_read == 2


def test_to_aiohttp_timeout_none_means_disabled() -> None:
    translated = _to_aiohttp_timeout(None)
    assert translated.total is None
