from __future__ import annotations

import warnings
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

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


def _patched_session_client(
    options: ClientOptions | None = None,
) -> tuple[AioHttpClient, MagicMock]:
    """Create AioHttpClient with TCPConnector and ClientSession patched; return (client, session_mock)."""
    with (
        patch("kubex.client.aiohttp.TCPConnector") as mock_connector,
        patch("kubex.client.aiohttp.ClientSession") as mock_session,
    ):
        mock_connector.return_value = MagicMock()
        mock_session.return_value = MagicMock()
        client = AioHttpClient(_config(), options)
    return client, mock_session


@pytest.mark.parametrize(
    "val,expected",
    [
        pytest.param(..., 2**21, id="ellipsis_kubex_default"),
        pytest.param(None, 0, id="none_no_cap"),
        pytest.param(8 * 1024 * 1024, 8 * 1024 * 1024, id="explicit_int"),
    ],
)
def test_resolve_ws_max_message_size(val: Any, expected: int) -> None:
    assert resolve_ws_max_message_size(val) == expected


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


@pytest.mark.anyio
async def test_aiohttp_pool_size_default_uses_library_default() -> None:
    # Ellipsis (default) must NOT pass limit at all — let aiohttp decide.
    from aiohttp.connector import TCPConnector as _RealTCPConnector

    with patch("kubex.client.aiohttp.TCPConnector", wraps=_RealTCPConnector) as spy:
        AioHttpClient(_config(), ClientOptions())
        init_kwargs = spy.call_args.kwargs
        assert "limit" not in init_kwargs


@pytest.mark.anyio
@pytest.mark.parametrize(
    "pool_size,expected_limit",
    [
        pytest.param(None, 0, id="none_unlimited"),
        pytest.param(50, 50, id="explicit_int"),
    ],
)
async def test_aiohttp_pool_size(pool_size: int | None, expected_limit: int) -> None:
    client = AioHttpClient(_config(), ClientOptions(pool_size=pool_size))
    assert client._inner_client.connector.limit == expected_limit


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


@pytest.mark.anyio
@pytest.mark.parametrize(
    "options,expected_force_close",
    [
        pytest.param(ClientOptions(), False, id="default_keep_alive"),
        pytest.param(ClientOptions(keep_alive=False), True, id="keep_alive_false"),
    ],
)
async def test_aiohttp_keep_alive_maps_to_force_close(
    options: ClientOptions, expected_force_close: bool
) -> None:
    client = AioHttpClient(_config(), options)
    force_close = getattr(client._inner_client.connector, "_force_close", None)
    assert force_close is expected_force_close


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


@pytest.mark.anyio
@pytest.mark.parametrize(
    "buffer_size,expected_bufsize",
    [
        pytest.param(..., 2**21, id="default_kubex_default"),
        pytest.param(None, 2**16, id="none_aiohttp_default"),
        pytest.param(4096, 4096, id="explicit_int"),
    ],
)
async def test_aiohttp_buffer_size(buffer_size: Any, expected_bufsize: int) -> None:
    client = AioHttpClient(_config(), ClientOptions(buffer_size=buffer_size))
    assert client._inner_client._read_bufsize == expected_bufsize


@pytest.mark.anyio
@pytest.mark.parametrize(
    "ws_max_message_size,expected_max_msg_size",
    [
        pytest.param(..., 2**21, id="default_kubex_default"),
        pytest.param(None, 0, id="none_no_cap"),
        pytest.param(8 * 1024 * 1024, 8 * 1024 * 1024, id="explicit_int"),
    ],
)
async def test_aiohttp_ws_max_message_size(
    ws_max_message_size: Any, expected_max_msg_size: int
) -> None:
    client = AioHttpClient(
        _config(), ClientOptions(ws_max_message_size=ws_max_message_size)
    )
    mock_ws = AsyncMock()
    mock_ws.protocol = None
    mock_ws.closed = False
    mock_ws_connect = AsyncMock(return_value=mock_ws)
    with patch.object(client._inner_client, "ws_connect", new=mock_ws_connect):
        request = Request(method="GET", url="/exec")
        await client.connect_websocket(request, [])
    assert mock_ws_connect.call_args.kwargs["max_msg_size"] == expected_max_msg_size


@pytest.mark.anyio
@pytest.mark.parametrize(
    "proxy,expected_proxy",
    [
        pytest.param(None, None, id="no_proxy"),
        pytest.param(
            "http://proxy.corp:8080", "http://proxy.corp:8080", id="proxy_str"
        ),
        pytest.param(
            {"https": "http://proxy.corp:8080"},
            "http://proxy.corp:8080",
            id="proxy_dict_matching_scheme",
        ),
    ],
)
async def test_aiohttp_session_kwargs_proxy(
    proxy: Any, expected_proxy: str | None
) -> None:
    client = AioHttpClient(_config(), ClientOptions(proxy=proxy))
    session_kw = client._session_kwargs()
    assert session_kw.get("proxy") == expected_proxy


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


@pytest.mark.parametrize(
    "options,expected",
    [
        pytest.param(ClientOptions(), False, id="default_false"),
        pytest.param(ClientOptions(trust_env=True), True, id="explicit_true"),
    ],
)
def test_trust_env_passed_to_session(options: ClientOptions, expected: bool) -> None:
    _, mock_session = _patched_session_client(options)
    _, kwargs = mock_session.call_args
    assert kwargs.get("trust_env") is expected


@pytest.mark.parametrize(
    "options,expected",
    [
        pytest.param(ClientOptions(), False, id="default_false"),
        pytest.param(ClientOptions(trust_env=True), True, id="explicit_true"),
    ],
)
def test_trust_env_propagated_to_session_kwargs(
    options: ClientOptions, expected: bool
) -> None:
    client, _ = _patched_session_client(options)
    session_kw = client._session_kwargs()
    assert session_kw.get("trust_env") is expected


def test_trust_env_false_default_with_env_set_aiohttp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HTTPS_PROXY", "http://leak.example.com:3128")
    _, mock_session = _patched_session_client(ClientOptions())
    _, kwargs = mock_session.call_args
    assert kwargs.get("trust_env") is False
    assert "proxy" not in kwargs


def test_trust_env_true_explicit_proxy_emits_warning_aiohttp() -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _, mock_session = _patched_session_client(
            ClientOptions(proxy="http://corp.proxy:8080", trust_env=True)
        )
    _, kwargs = mock_session.call_args
    assert any(
        issubclass(w.category, UserWarning)
        and "proxy" in str(w.message)
        and "trust_env" in str(w.message)
        for w in caught
    )
    assert kwargs.get("trust_env") is False


def test_trust_env_true_explicit_proxy_session_kwargs_force_false_aiohttp() -> None:
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        client, _ = _patched_session_client(
            ClientOptions(proxy="http://corp.proxy:8080", trust_env=True)
        )
    session_kw = client._session_kwargs()
    assert session_kw.get("trust_env") is False


def test_trust_env_true_proxy_dict_no_matching_scheme_does_not_disable_trust_env() -> (
    None
):
    # proxy={"http": ...} against an https:// API server — aiohttp applies no
    # effective proxy (wrong scheme). trust_env must NOT be force-disabled just
    # because the raw options.proxy dict is non-None.
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _, mock_session = _patched_session_client(
            ClientOptions(proxy={"http": "http://corp.proxy:8080"}, trust_env=True)
        )
    _, kwargs = mock_session.call_args
    # "no entry for URL scheme" warning must fire (from _apply_aiohttp_proxy)
    assert any(
        issubclass(w.category, UserWarning)
        and "no entry for URL scheme" in str(w.message)
        for w in caught
    )
    # conflict warning must NOT fire — no proxy was actually applied
    assert not any(
        issubclass(w.category, UserWarning)
        and "trust_env" in str(w.message)
        and "proxy" in str(w.message)
        and "ignored" in str(w.message)
        for w in caught
    )
    assert kwargs.get("trust_env") is True
