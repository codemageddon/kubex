from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from kubex.client.client import ClientChoise, _try_read_configuration, create_client
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
async def test_try_read_configuration_falls_back_to_incluster_on_missing_kubeconfig() -> (
    None
):
    in_cluster_config = ClientConfiguration(
        url="https://kubernetes.default.svc", insecure_skip_tls_verify=True
    )
    with (
        patch(
            "kubex.client.client.configure_from_kubeconfig",
            new_callable=AsyncMock,
            side_effect=FileNotFoundError,
        ),
        patch(
            "kubex.client.client.configure_from_pod_env",
            new_callable=AsyncMock,
            return_value=in_cluster_config,
        ) as mock_pod_env,
    ):
        config = await _try_read_configuration()
        mock_pod_env.assert_awaited_once()
        assert config is in_cluster_config


@pytest.mark.anyio
async def test_try_read_configuration_propagates_non_file_not_found_errors() -> None:
    with patch(
        "kubex.client.client.configure_from_kubeconfig",
        new_callable=AsyncMock,
        side_effect=ValueError("malformed kubeconfig"),
    ):
        with pytest.raises(ValueError, match="malformed kubeconfig"):
            await _try_read_configuration()


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
