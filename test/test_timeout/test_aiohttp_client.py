from __future__ import annotations

import pytest

from kubex.client.options import ClientOptions
from kubex.configuration import ClientConfiguration
from kubex.core.params import Timeout

aiohttp = pytest.importorskip("aiohttp")

from kubex.client.aiohttp import AioHttpClient, _to_aiohttp_timeout  # noqa: E402


def _configuration() -> ClientConfiguration:
    return ClientConfiguration(url="https://example.invalid")


@pytest.mark.anyio
async def test_create_inner_session_with_ellipsis_uses_aiohttp_default() -> None:
    from aiohttp.client import DEFAULT_TIMEOUT

    client = AioHttpClient(_configuration())
    try:
        assert client._inner_client.timeout == DEFAULT_TIMEOUT
    finally:
        await client.close()


@pytest.mark.anyio
async def test_create_inner_session_with_timeout() -> None:
    client = AioHttpClient(_configuration(), ClientOptions(timeout=5))
    try:
        assert client._inner_client.timeout.total == 5
    finally:
        await client.close()


@pytest.mark.anyio
async def test_create_inner_session_with_none_disables_timeout() -> None:
    client = AioHttpClient(_configuration(), ClientOptions(timeout=None))
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


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("client_timeout", "expected"),
    [
        pytest.param(
            ...,
            {"total": None, "connect": 300, "sock_connect": 30, "sock_read": None},
            id="default",
        ),
        pytest.param(
            Timeout(total=30),
            {"total": None, "connect": 30, "sock_connect": None, "sock_read": None},
            id="total",
        ),
        pytest.param(
            Timeout(connect=2, read=60),
            {"total": None, "connect": None, "sock_connect": 2, "sock_read": None},
            id="connect-read",
        ),
        pytest.param(
            None,
            {"total": None, "connect": None, "sock_connect": None, "sock_read": None},
            id="disabled",
        ),
    ],
)
async def test_stream_timeout_keeps_connection_bounds_and_drops_total_and_read(
    client_timeout: object, expected: dict[str, float | None]
) -> None:
    client = AioHttpClient(_configuration(), ClientOptions(timeout=client_timeout))
    try:
        timeout = client._stream_timeout()
        assert {name: getattr(timeout, name) for name in expected} == expected
    finally:
        await client.close()
