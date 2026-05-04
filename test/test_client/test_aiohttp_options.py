from __future__ import annotations

import warnings
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from kubex.client.options import ClientOptions
from kubex.configuration import ClientConfiguration

pytest.importorskip("aiohttp")

from kubex.client.aiohttp import (  # noqa: E402
    AioHttpClient,
    _apply_aiohttp_proxy,
)
from kubex.client.options import resolve_ws_max_message_size  # noqa: E402
from kubex.core.request import Request  # noqa: E402


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _config() -> ClientConfiguration:
    return ClientConfiguration(
        url="https://example.invalid", insecure_skip_tls_verify=True
    )


# --- resolve_ws_max_message_size ---


def test_resolve_ws_max_message_size_ellipsis_returns_kubex_default() -> None:
    assert resolve_ws_max_message_size(...) == 2**21


def test_resolve_ws_max_message_size_none_returns_zero() -> None:
    assert resolve_ws_max_message_size(None) == 0


def test_resolve_ws_max_message_size_explicit_int() -> None:
    assert resolve_ws_max_message_size(8 * 1024 * 1024) == 8 * 1024 * 1024


# --- _apply_aiohttp_proxy ---


def test_apply_aiohttp_proxy_none_no_op() -> None:
    kwargs: dict[str, Any] = {}
    _apply_aiohttp_proxy(kwargs, None, "https://api.example.com")
    assert "proxy" not in kwargs


def test_apply_aiohttp_proxy_str_sets_proxy() -> None:
    kwargs: dict[str, Any] = {}
    _apply_aiohttp_proxy(kwargs, "http://proxy.corp:8080", "https://api.example.com")
    assert kwargs["proxy"] == "http://proxy.corp:8080"


def test_apply_aiohttp_proxy_dict_matching_scheme_sets_proxy() -> None:
    kwargs: dict[str, Any] = {}
    _apply_aiohttp_proxy(
        kwargs,
        {"https": "http://proxy.corp:8080"},
        "https://api.example.com",
    )
    assert kwargs["proxy"] == "http://proxy.corp:8080"


def test_apply_aiohttp_proxy_dict_matching_scheme_drops_extra_with_warning() -> None:
    kwargs: dict[str, Any] = {}
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _apply_aiohttp_proxy(
            kwargs,
            {"http": "http://proxy.corp:8080", "https": "http://proxy.corp:8443"},
            "https://api.example.com",
        )
    assert kwargs["proxy"] == "http://proxy.corp:8443"
    assert any(
        issubclass(w.category, UserWarning)
        and "Dropped proxy scheme entries" in str(w.message)
        for w in caught
    )


def test_apply_aiohttp_proxy_dict_no_matching_scheme_warns_no_proxy() -> None:
    kwargs: dict[str, Any] = {}
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _apply_aiohttp_proxy(
            kwargs,
            {"http": "http://proxy.corp:8080"},
            "https://api.example.com",
        )
    assert "proxy" not in kwargs
    assert any(
        issubclass(w.category, UserWarning)
        and "no entry for URL scheme" in str(w.message)
        for w in caught
    )


# --- connector: pool_size ---


@pytest.mark.anyio
async def test_aiohttp_pool_size_default_uses_library_default() -> None:
    # Ellipsis (default) must NOT pass limit at all — let aiohttp decide.
    from aiohttp.connector import TCPConnector as _RealTCPConnector

    with patch("kubex.client.aiohttp.TCPConnector", wraps=_RealTCPConnector) as spy:
        AioHttpClient(_config(), ClientOptions())
        init_kwargs = spy.call_args.kwargs
        assert "limit" not in init_kwargs


@pytest.mark.anyio
async def test_aiohttp_pool_size_none_sets_unlimited() -> None:
    client = AioHttpClient(_config(), ClientOptions(pool_size=None))
    assert client._inner_client.connector.limit == 0


@pytest.mark.anyio
async def test_aiohttp_pool_size_explicit_int() -> None:
    client = AioHttpClient(_config(), ClientOptions(pool_size=50))
    assert client._inner_client.connector.limit == 50


# --- connector: pool_size_per_host ---


@pytest.mark.anyio
async def test_aiohttp_pool_size_per_host_default_uses_library_default() -> None:
    # Ellipsis (default) must NOT pass limit_per_host at all — let aiohttp decide.
    from aiohttp.connector import TCPConnector as _RealTCPConnector

    with patch("kubex.client.aiohttp.TCPConnector", wraps=_RealTCPConnector) as spy:
        AioHttpClient(_config(), ClientOptions())
        init_kwargs = spy.call_args.kwargs
        assert "limit_per_host" not in init_kwargs


@pytest.mark.anyio
async def test_aiohttp_pool_size_per_host_none_sets_zero() -> None:
    # pool_size_per_host=None must explicitly pass limit_per_host=0; the default
    # (Ellipsis) does NOT pass the kwarg at all. Both produce the same observable
    # connector attribute (0 == aiohttp's default), so we spy on TCPConnector to
    # verify the kwarg was actually forwarded.
    from aiohttp.connector import TCPConnector as _RealTCPConnector

    with patch("kubex.client.aiohttp.TCPConnector", wraps=_RealTCPConnector) as spy:
        AioHttpClient(_config(), ClientOptions(pool_size_per_host=None))
        init_kwargs = spy.call_args.kwargs
        assert "limit_per_host" in init_kwargs
        assert init_kwargs["limit_per_host"] == 0


@pytest.mark.anyio
async def test_aiohttp_pool_size_per_host_explicit_int() -> None:
    client = AioHttpClient(_config(), ClientOptions(pool_size_per_host=5))
    assert client._inner_client.connector.limit_per_host == 5


# --- connector: keep_alive ---


@pytest.mark.anyio
async def test_aiohttp_keep_alive_true_default_no_force_close() -> None:
    client = AioHttpClient(_config(), ClientOptions())
    force_close = getattr(client._inner_client.connector, "_force_close", False)
    assert force_close is False


@pytest.mark.anyio
async def test_aiohttp_keep_alive_false_sets_force_close() -> None:
    client = AioHttpClient(_config(), ClientOptions(keep_alive=False))
    force_close = getattr(client._inner_client.connector, "_force_close", None)
    assert force_close is True


# --- connector: keep_alive_timeout ---


@pytest.mark.anyio
async def test_aiohttp_keep_alive_timeout_default_uses_library_default() -> None:
    client = AioHttpClient(_config(), ClientOptions())
    timeout = getattr(client._inner_client.connector, "_keepalive_timeout", None)
    assert timeout == 15.0  # aiohttp default


@pytest.mark.anyio
async def test_aiohttp_keep_alive_timeout_none_warns_and_uses_library_default() -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        client = AioHttpClient(_config(), ClientOptions(keep_alive_timeout=None))
    assert any(
        issubclass(w.category, UserWarning)
        and "keep_alive_timeout=None is not supported" in str(w.message)
        for w in caught
    )
    # aiohttp uses its own default (15 s) when keep_alive_timeout=None
    timeout = getattr(client._inner_client.connector, "_keepalive_timeout", None)
    assert timeout == 15.0


@pytest.mark.anyio
async def test_aiohttp_keep_alive_timeout_explicit_float() -> None:
    client = AioHttpClient(_config(), ClientOptions(keep_alive_timeout=60.0))
    timeout = getattr(client._inner_client.connector, "_keepalive_timeout", None)
    assert timeout == 60.0


@pytest.mark.anyio
async def test_aiohttp_keep_alive_false_with_timeout_does_not_raise() -> None:
    # force_close=True and keepalive_timeout together would raise ValueError in aiohttp;
    # when keep_alive=False the timeout setting must be silently ignored.
    client = AioHttpClient(
        _config(), ClientOptions(keep_alive=False, keep_alive_timeout=60.0)
    )
    force_close = getattr(client._inner_client.connector, "_force_close", None)
    assert force_close is True


# --- session: buffer_size ---


@pytest.mark.anyio
async def test_aiohttp_buffer_size_default_is_kubex_default() -> None:
    client = AioHttpClient(_config(), ClientOptions())
    assert client._inner_client._read_bufsize == 2**21


@pytest.mark.anyio
async def test_aiohttp_buffer_size_none_uses_library_default() -> None:
    client = AioHttpClient(_config(), ClientOptions(buffer_size=None))
    # aiohttp library default is 2**16
    assert client._inner_client._read_bufsize == 2**16


@pytest.mark.anyio
async def test_aiohttp_buffer_size_explicit_int() -> None:
    client = AioHttpClient(_config(), ClientOptions(buffer_size=4096))
    assert client._inner_client._read_bufsize == 4096


# --- ws_max_message_size ---


@pytest.mark.anyio
async def test_aiohttp_ws_max_message_size_default() -> None:
    client = AioHttpClient(_config(), ClientOptions())
    mock_ws = AsyncMock()
    mock_ws.protocol = None
    mock_ws.closed = False
    mock_ws_connect = AsyncMock(return_value=mock_ws)
    with patch.object(client._inner_client, "ws_connect", new=mock_ws_connect):
        request = Request(method="GET", url="/exec")
        await client.connect_websocket(request, [])
    assert mock_ws_connect.call_args.kwargs["max_msg_size"] == 2**21


@pytest.mark.anyio
async def test_aiohttp_ws_max_message_size_none_no_cap() -> None:
    client = AioHttpClient(_config(), ClientOptions(ws_max_message_size=None))
    mock_ws = AsyncMock()
    mock_ws.protocol = None
    mock_ws.closed = False
    mock_ws_connect = AsyncMock(return_value=mock_ws)
    with patch.object(client._inner_client, "ws_connect", new=mock_ws_connect):
        request = Request(method="GET", url="/exec")
        await client.connect_websocket(request, [])
    assert mock_ws_connect.call_args.kwargs["max_msg_size"] == 0


@pytest.mark.anyio
async def test_aiohttp_ws_max_message_size_explicit() -> None:
    client = AioHttpClient(
        _config(), ClientOptions(ws_max_message_size=8 * 1024 * 1024)
    )
    mock_ws = AsyncMock()
    mock_ws.protocol = None
    mock_ws.closed = False
    mock_ws_connect = AsyncMock(return_value=mock_ws)
    with patch.object(client._inner_client, "ws_connect", new=mock_ws_connect):
        request = Request(method="GET", url="/exec")
        await client.connect_websocket(request, [])
    assert mock_ws_connect.call_args.kwargs["max_msg_size"] == 8 * 1024 * 1024


# --- proxy integration: propagated through _session_kwargs ---


@pytest.mark.anyio
async def test_aiohttp_session_kwargs_includes_proxy_str() -> None:
    client = AioHttpClient(_config(), ClientOptions(proxy="http://proxy.corp:8080"))
    session_kw = client._session_kwargs()
    assert session_kw.get("proxy") == "http://proxy.corp:8080"


@pytest.mark.anyio
async def test_aiohttp_session_kwargs_no_proxy_by_default() -> None:
    client = AioHttpClient(_config(), ClientOptions())
    session_kw = client._session_kwargs()
    assert "proxy" not in session_kw


@pytest.mark.anyio
async def test_aiohttp_session_kwargs_includes_proxy_dict_matching_scheme() -> None:
    client = AioHttpClient(
        _config(), ClientOptions(proxy={"https": "http://proxy.corp:8080"})
    )
    session_kw = client._session_kwargs()
    assert session_kw.get("proxy") == "http://proxy.corp:8080"


# --- regression: defaults preserve prior behavior ---


@pytest.mark.anyio
async def test_aiohttp_default_options_regression() -> None:
    client = AioHttpClient(_config(), ClientOptions())
    session = client._inner_client
    connector = session.connector

    # read buffer: 2**21 (kubex default — must not regress to aiohttp's 2**16)
    assert session._read_bufsize == 2**21

    # pool total: aiohttp default 100
    assert connector.limit == 100

    # per-host: aiohttp default 0 (unlimited)
    assert connector.limit_per_host == 0

    # keep-alive: on by default
    force_close = getattr(connector, "_force_close", False)
    assert force_close is False

    # no proxy
    session_kw = client._session_kwargs()
    assert "proxy" not in session_kw
