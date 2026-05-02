from __future__ import annotations

import pytest

from kubex.client.client import ClientChoise, create_client
from kubex.client.options import ClientOptions
from kubex.configuration import ClientConfiguration

httpx = pytest.importorskip("httpx")


def _config() -> ClientConfiguration:
    return ClientConfiguration(
        url="https://example.invalid", insecure_skip_tls_verify=True
    )


@pytest.mark.anyio
async def test_create_client_defaults_options() -> None:
    client = await create_client(_config(), client_class=ClientChoise.HTTPX)
    assert isinstance(client.options, ClientOptions)
    assert client.options.timeout is Ellipsis
    assert client.options.log_api_warnings is True
    await client.close()


@pytest.mark.anyio
async def test_create_client_propagates_explicit_options() -> None:
    opts = ClientOptions(log_api_warnings=False, timeout=10)
    client = await create_client(
        _config(), options=opts, client_class=ClientChoise.HTTPX
    )
    assert client.options is opts
    await client.close()


@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio"])
async def test_create_client_auto_propagates_options() -> None:
    pytest.importorskip("aiohttp")
    from kubex.client.aiohttp import AioHttpClient

    opts = ClientOptions(log_api_warnings=False)
    client = await create_client(
        _config(), options=opts, client_class=ClientChoise.AUTO
    )
    assert isinstance(client, AioHttpClient)
    assert client.options is opts
    await client.close()


@pytest.mark.anyio
async def test_create_client_none_options_gives_defaults() -> None:
    client = await create_client(
        _config(), options=None, client_class=ClientChoise.HTTPX
    )
    assert isinstance(client.options, ClientOptions)
    assert client.options.timeout is Ellipsis
    await client.close()


@pytest.mark.anyio
async def test_create_client_rejects_non_options_as_options() -> None:
    with pytest.raises(TypeError, match="options must be a ClientOptions instance"):
        await create_client(
            _config(),
            options=ClientChoise.HTTPX,  # type: ignore[arg-type]
            client_class=ClientChoise.HTTPX,
        )


@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio"])
async def test_create_client_aiohttp_propagates_options() -> None:
    pytest.importorskip("aiohttp")
    from kubex.client.aiohttp import AioHttpClient

    opts = ClientOptions(log_api_warnings=False, timeout=5)
    client = await create_client(
        _config(), options=opts, client_class=ClientChoise.AIOHTTP
    )
    assert isinstance(client, AioHttpClient)
    assert client.options is opts
    await client.close()
