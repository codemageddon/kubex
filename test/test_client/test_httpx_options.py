from __future__ import annotations

import warnings
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytest.importorskip("httpx")
pytest.importorskip("httpx_ws")

import httpx  # noqa: E402

from kubex.client.httpx import (  # noqa: E402
    HttpxClient,
    _build_httpx_limits,
    _build_httpx_proxy_kwargs,
)
from kubex.client.options import resolve_ws_max_message_size  # noqa: E402
from kubex.client.options import ClientOptions  # noqa: E402
from kubex.configuration import ClientConfiguration  # noqa: E402
from kubex.core.request import Request  # noqa: E402


def _config() -> ClientConfiguration:
    return ClientConfiguration(
        url="https://example.invalid", insecure_skip_tls_verify=True
    )


def _client(options: ClientOptions | None = None) -> HttpxClient:
    return HttpxClient(_config(), options)


# ---------------------------------------------------------------------------
# resolve_ws_max_message_size
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "val,expected",
    [
        pytest.param(..., 2**21, id="ellipsis_kubex_default"),
        pytest.param(None, 0, id="none_no_cap"),
        pytest.param(4 * 1024 * 1024, 4 * 1024 * 1024, id="explicit_int"),
    ],
)
def test_resolve_ws_max_message_size(val: Any, expected: int) -> None:
    assert resolve_ws_max_message_size(val) == expected


# ---------------------------------------------------------------------------
# _build_httpx_limits
# ---------------------------------------------------------------------------


def test_build_httpx_limits_all_defaults_returns_empty() -> None:
    opts = ClientOptions()
    assert _build_httpx_limits(opts) == {}


def test_build_httpx_limits_keep_alive_false() -> None:
    opts = ClientOptions(keep_alive=False)
    kw = _build_httpx_limits(opts)
    assert kw["max_keepalive_connections"] == 0


def test_build_httpx_limits_pool_size_int() -> None:
    opts = ClientOptions(pool_size=50)
    kw = _build_httpx_limits(opts)
    assert kw["max_connections"] == 50


def test_build_httpx_limits_pool_size_none_unlimited() -> None:
    opts = ClientOptions(pool_size=None)
    kw = _build_httpx_limits(opts)
    assert kw["max_connections"] is None


def test_build_httpx_limits_keep_alive_timeout_float() -> None:
    opts = ClientOptions(keep_alive_timeout=30.0)
    kw = _build_httpx_limits(opts)
    assert kw["keepalive_expiry"] == 30.0


def test_build_httpx_limits_keep_alive_timeout_none() -> None:
    opts = ClientOptions(keep_alive_timeout=None)
    kw = _build_httpx_limits(opts)
    assert kw["keepalive_expiry"] is None


def test_build_httpx_limits_combined() -> None:
    opts = ClientOptions(pool_size=20, keep_alive=False, keep_alive_timeout=60.0)
    kw = _build_httpx_limits(opts)
    assert kw["max_connections"] == 20
    assert kw["max_keepalive_connections"] == 0
    assert kw["keepalive_expiry"] == 60.0


# ---------------------------------------------------------------------------
# _build_httpx_proxy_kwargs
# ---------------------------------------------------------------------------


def test_build_httpx_proxy_kwargs_none_returns_empty() -> None:
    import ssl

    ctx = ssl.create_default_context()
    assert _build_httpx_proxy_kwargs(None, ctx) == {}


def test_build_httpx_proxy_kwargs_str_returns_proxy_key() -> None:
    import ssl

    ctx = ssl.create_default_context()
    url = "http://proxy.example.com:8080"
    kw = _build_httpx_proxy_kwargs(url, ctx)
    assert kw == {"proxy": url}


def test_build_httpx_proxy_kwargs_dict_builds_mounts() -> None:
    import ssl

    ctx = ssl.create_default_context()
    proxy_dict = {"https": "http://proxy.example.com:8080"}
    kw = _build_httpx_proxy_kwargs(proxy_dict, ctx)
    assert "mounts" in kw
    mounts = kw["mounts"]
    assert "https://" in mounts
    assert isinstance(mounts["https://"], httpx.AsyncHTTPTransport)


def test_build_httpx_proxy_kwargs_dict_both_schemes() -> None:
    import ssl

    ctx = ssl.create_default_context()
    proxy_dict = {
        "http": "http://proxy.example.com:8080",
        "https": "http://proxy.example.com:8080",
    }
    kw = _build_httpx_proxy_kwargs(proxy_dict, ctx)
    mounts = kw["mounts"]
    assert "http://" in mounts
    assert "https://" in mounts


# ---------------------------------------------------------------------------
# HttpxClient._create_inner_client — option wiring
# ---------------------------------------------------------------------------


def _pool(client: HttpxClient) -> Any:
    """Navigate httpx.AsyncClient -> AsyncHTTPTransport -> httpcore pool."""
    return client._inner_client._transport._pool


def test_create_inner_client_defaults_no_limits_kwarg() -> None:
    client = _client(ClientOptions())
    assert isinstance(client._inner_client, httpx.AsyncClient)


def test_create_inner_client_pool_size_wired() -> None:
    client = _client(ClientOptions(pool_size=42))
    assert _pool(client)._max_connections == 42


def test_create_inner_client_pool_size_none_means_unlimited() -> None:
    import sys

    client = _client(ClientOptions(pool_size=None))
    # httpcore converts None → sys.maxsize internally (unlimited sentinel)
    assert _pool(client)._max_connections == sys.maxsize


def test_create_inner_client_keep_alive_false_sets_zero_keepalive() -> None:
    client = _client(ClientOptions(keep_alive=False))
    assert _pool(client)._max_keepalive_connections == 0


def test_create_inner_client_keep_alive_timeout() -> None:
    client = _client(ClientOptions(keep_alive_timeout=45.0))
    assert _pool(client)._keepalive_expiry == 45.0


def test_create_inner_client_proxy_str() -> None:
    import httpcore

    client = _client(ClientOptions(proxy="http://proxy.example.com:8080"))
    inner = client._inner_client
    # A str proxy creates an httpcore.AsyncHTTPProxy pool behind at least one
    # of the transports in _mounts.
    assert any(
        isinstance(getattr(v, "_pool", None), httpcore.AsyncHTTPProxy)
        for v in inner._mounts.values()
    )


def test_create_inner_client_proxy_dict() -> None:
    proxy_dict = {"https": "http://proxy.example.com:8080"}
    client = _client(ClientOptions(proxy=proxy_dict))
    inner = client._inner_client
    # Dict proxy uses mounts=; httpx stores URLPattern objects as keys so we
    # match by the pattern attribute.
    https_transport = next(
        (
            v
            for k, v in inner._mounts.items()
            if getattr(k, "pattern", None) == "https://"
        ),
        None,
    )
    assert isinstance(https_transport, httpx.AsyncHTTPTransport)


def test_create_inner_client_no_proxy_by_default() -> None:
    client = _client(ClientOptions())
    assert isinstance(client._inner_client, httpx.AsyncClient)


def test_create_inner_client_buffer_size_not_ellipsis_warns() -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _client(ClientOptions(buffer_size=65536))
    assert any(
        issubclass(w.category, UserWarning) and "buffer_size" in str(w.message)
        for w in caught
    )


def test_create_inner_client_buffer_size_none_warns() -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _client(ClientOptions(buffer_size=None))
    assert any(
        issubclass(w.category, UserWarning) and "buffer_size" in str(w.message)
        for w in caught
    )


def test_create_inner_client_buffer_size_ellipsis_no_warn() -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _client(ClientOptions(buffer_size=...))
    buffer_warns = [
        w
        for w in caught
        if issubclass(w.category, UserWarning) and "buffer_size" in str(w.message)
    ]
    assert not buffer_warns


def test_create_inner_client_pool_size_per_host_not_ellipsis_warns() -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _client(ClientOptions(pool_size_per_host=10))
    assert any(
        issubclass(w.category, UserWarning) and "pool_size_per_host" in str(w.message)
        for w in caught
    )


def test_create_inner_client_pool_size_per_host_none_warns() -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _client(ClientOptions(pool_size_per_host=None))
    assert any(
        issubclass(w.category, UserWarning) and "pool_size_per_host" in str(w.message)
        for w in caught
    )


def test_create_inner_client_pool_size_per_host_ellipsis_no_warn() -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _client(ClientOptions(pool_size_per_host=...))
    per_host_warns = [
        w
        for w in caught
        if issubclass(w.category, UserWarning)
        and "pool_size_per_host" in str(w.message)
    ]
    assert not per_host_warns


# ---------------------------------------------------------------------------
# connect_websocket — ws_max_message_size
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_connect_websocket_default_max_message_size() -> None:
    client = _client(ClientOptions())
    request = Request(method="GET", url="/ws")

    with patch("httpx_ws.aconnect_ws") as mock_connect:
        mock_session = MagicMock()
        mock_session.subprotocol = "v5.channel.k8s.io"
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cm.__aexit__ = AsyncMock(return_value=None)
        mock_connect.return_value = mock_cm

        conn = await client.connect_websocket(request, ["v5.channel.k8s.io"])
        await conn.close()

    _, kwargs = mock_connect.call_args
    assert kwargs.get("max_message_size_bytes") == 2**21


@pytest.mark.anyio
async def test_connect_websocket_none_max_message_size_warns_and_skips_param() -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        client = _client(ClientOptions(ws_max_message_size=None))

    assert any(
        issubclass(w.category, UserWarning) and "ws_max_message_size" in str(w.message)
        for w in caught
    )

    request = Request(method="GET", url="/ws")

    with patch("httpx_ws.aconnect_ws") as mock_connect:
        mock_session = MagicMock()
        mock_session.subprotocol = "v5.channel.k8s.io"
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cm.__aexit__ = AsyncMock(return_value=None)
        mock_connect.return_value = mock_cm

        conn = await client.connect_websocket(request, ["v5.channel.k8s.io"])
        await conn.close()

    _, kwargs = mock_connect.call_args
    assert "max_message_size_bytes" not in kwargs


@pytest.mark.anyio
async def test_connect_websocket_explicit_max_message_size() -> None:
    explicit_size = 8 * 1024 * 1024
    client = _client(ClientOptions(ws_max_message_size=explicit_size))
    request = Request(method="GET", url="/ws")

    with patch("httpx_ws.aconnect_ws") as mock_connect:
        mock_session = MagicMock()
        mock_session.subprotocol = "v5.channel.k8s.io"
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cm.__aexit__ = AsyncMock(return_value=None)
        mock_connect.return_value = mock_cm

        conn = await client.connect_websocket(request, ["v5.channel.k8s.io"])
        await conn.close()

    _, kwargs = mock_connect.call_args
    assert kwargs.get("max_message_size_bytes") == explicit_size


# ---------------------------------------------------------------------------
# Regression: ClientOptions() defaults produce identical behavior to pre-option code
# ---------------------------------------------------------------------------


def test_regression_defaults_no_limits_no_proxy() -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        client = _client(ClientOptions())

    # No user-facing warnings with all defaults
    user_warnings = [w for w in caught if issubclass(w.category, UserWarning)]
    assert not user_warnings

    inner = client._inner_client
    assert isinstance(inner, httpx.AsyncClient)
    # Default limits should be httpx's own defaults (not our custom object)
    # when all pool/keep-alive fields are ...
    pool = _pool(client)
    # httpx default: max_connections=100, max_keepalive_connections=20, keepalive_expiry=5.0
    assert pool._max_connections == 100
    assert pool._max_keepalive_connections == 20
    assert pool._keepalive_expiry == 5.0
