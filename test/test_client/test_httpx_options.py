from __future__ import annotations

import ssl
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


def _patched_client(
    options: ClientOptions | None = None,
) -> tuple[HttpxClient, MagicMock]:
    """Create an HttpxClient with httpx.AsyncClient patched; return (client, mock)."""
    with patch("kubex.client.httpx.httpx.AsyncClient") as mock_ac:
        mock_ac.return_value = MagicMock()
        client = HttpxClient(_config(), options)
    return client, mock_ac


def _config() -> ClientConfiguration:
    return ClientConfiguration(
        url="https://example.invalid", insecure_skip_tls_verify=True
    )


def _client(options: ClientOptions | None = None) -> HttpxClient:
    return HttpxClient(_config(), options)


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


def test_build_httpx_limits_all_defaults_returns_empty() -> None:
    assert _build_httpx_limits(ClientOptions()) == {}


@pytest.mark.parametrize(
    "options,expected_subset",
    [
        pytest.param(
            ClientOptions(keep_alive=False),
            {"max_keepalive_connections": 0},
            id="keep_alive_false",
        ),
        pytest.param(
            ClientOptions(pool_size=50),
            {"max_connections": 50},
            id="pool_size_int",
        ),
        pytest.param(
            ClientOptions(pool_size=None),
            {"max_connections": None},
            id="pool_size_none_unlimited",
        ),
        pytest.param(
            ClientOptions(keep_alive_timeout=30.0),
            {"keepalive_expiry": 30.0},
            id="keep_alive_timeout_float",
        ),
        pytest.param(
            ClientOptions(keep_alive_timeout=None),
            {"keepalive_expiry": None},
            id="keep_alive_timeout_none",
        ),
        pytest.param(
            ClientOptions(pool_size=20, keep_alive=False, keep_alive_timeout=60.0),
            {
                "max_connections": 20,
                "max_keepalive_connections": 0,
                "keepalive_expiry": 60.0,
            },
            id="combined",
        ),
    ],
)
def test_build_httpx_limits(
    options: ClientOptions, expected_subset: dict[str, Any]
) -> None:
    kw = _build_httpx_limits(options)
    assert expected_subset.items() <= kw.items()


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


# httpx has no equivalent for buffer_size / pool_size_per_host. Setting either
# to anything other than ``...`` must emit a UserWarning mentioning the field;
# the default (``...``) must not.
@pytest.mark.parametrize(
    "field,value,expect_warn",
    [
        pytest.param("buffer_size", 65536, True, id="buffer_size_int_warns"),
        pytest.param("buffer_size", None, True, id="buffer_size_none_warns"),
        pytest.param("buffer_size", ..., False, id="buffer_size_ellipsis_no_warn"),
        pytest.param("pool_size_per_host", 10, True, id="pool_size_per_host_int_warns"),
        pytest.param(
            "pool_size_per_host", None, True, id="pool_size_per_host_none_warns"
        ),
        pytest.param(
            "pool_size_per_host", ..., False, id="pool_size_per_host_ellipsis_no_warn"
        ),
    ],
)
def test_create_inner_client_unsupported_field_warns(
    field: str, value: Any, expect_warn: bool
) -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _client(ClientOptions(**{field: value}))
    matching = [
        w
        for w in caught
        if issubclass(w.category, UserWarning) and field in str(w.message)
    ]
    assert bool(matching) is expect_warn


async def _connect_ws_and_get_kwargs(client: HttpxClient) -> dict[str, Any]:
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
    return dict(kwargs)


@pytest.mark.anyio
@pytest.mark.parametrize(
    "ws_max_message_size,expected",
    [
        pytest.param(..., 2**21, id="default_kubex_default"),
        pytest.param(8 * 1024 * 1024, 8 * 1024 * 1024, id="explicit_int"),
    ],
)
async def test_connect_websocket_forwards_max_message_size(
    ws_max_message_size: Any, expected: int
) -> None:
    client = _client(ClientOptions(ws_max_message_size=ws_max_message_size))
    kwargs = await _connect_ws_and_get_kwargs(client)
    assert kwargs.get("max_message_size_bytes") == expected


@pytest.mark.anyio
async def test_connect_websocket_none_max_message_size_warns_and_skips_param() -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        client = _client(ClientOptions(ws_max_message_size=None))

    assert any(
        issubclass(w.category, UserWarning) and "ws_max_message_size" in str(w.message)
        for w in caught
    )

    kwargs = await _connect_ws_and_get_kwargs(client)
    assert "max_message_size_bytes" not in kwargs


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


def test_trust_env_false_default_passed_to_async_client() -> None:
    _, mock_ac = _patched_client(ClientOptions())
    _, kwargs = mock_ac.call_args
    assert kwargs.get("trust_env") is False


def test_trust_env_false_default_overrides_httpx_library_default_with_env_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HTTPS_PROXY", "http://leak.example.com:3128")
    _, mock_ac = _patched_client(ClientOptions())
    _, kwargs = mock_ac.call_args
    assert kwargs.get("trust_env") is False
    assert "proxy" not in kwargs
    assert "mounts" not in kwargs


def test_trust_env_true_passed_to_async_client() -> None:
    _, mock_ac = _patched_client(ClientOptions(trust_env=True))
    _, kwargs = mock_ac.call_args
    assert kwargs.get("trust_env") is True
    assert "auth" not in kwargs


def test_trust_env_true_explicit_proxy_emits_warning() -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _, mock_ac = _patched_client(
            ClientOptions(proxy="http://corp.proxy:8080", trust_env=True)
        )
    _, kwargs = mock_ac.call_args
    assert any(
        issubclass(w.category, UserWarning)
        and "proxy" in str(w.message)
        and "trust_env" in str(w.message)
        for w in caught
    )
    assert kwargs.get("proxy") == "http://corp.proxy:8080"
    assert kwargs.get("trust_env") is False


def test_trust_env_true_explicit_proxy_preserves_ssl_cert_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # When trust_env=True + explicit proxy conflict, trust_env=False is passed
    # to httpx which also suppresses SSL_CERT_FILE. kubex must apply SSL_CERT_FILE
    # manually so callers relying on env-provided CA bundles are not silently
    # downgraded to certifi. Use a config without insecure_skip_tls_verify so
    # needs_custom_ssl=False and the SSL_CERT_FILE branch is exercised (not
    # masked by the pre-existing custom-ssl path).
    monkeypatch.setenv("SSL_CERT_FILE", "/path/to/custom_ca.pem")
    monkeypatch.delenv("SSL_CERT_DIR", raising=False)
    fake_ssl_ctx = MagicMock(spec=ssl.SSLContext)
    cfg = ClientConfiguration(url="https://example.invalid")
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        with (
            patch("kubex.client.httpx.httpx.AsyncClient") as mock_ac,
            patch(
                "kubex.client.httpx.ssl.create_default_context",
                return_value=fake_ssl_ctx,
            ) as mock_ctx,
        ):
            mock_ac.return_value = MagicMock()
            HttpxClient(
                cfg, ClientOptions(proxy="http://corp.proxy:8080", trust_env=True)
            )
    _, kwargs = mock_ac.call_args
    assert kwargs.get("trust_env") is False
    assert kwargs.get("verify") is fake_ssl_ctx
    mock_ctx.assert_called_once_with(cafile="/path/to/custom_ca.pem", capath=None)


def test_trust_env_true_explicit_proxy_preserves_ssl_cert_dir(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # SSL_CERT_DIR set (no SSL_CERT_FILE) — capath must be forwarded to
    # ssl.create_default_context when trust_env=True + explicit proxy conflict.
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    monkeypatch.setenv("SSL_CERT_DIR", "/path/to/cert/dir")
    fake_ssl_ctx = MagicMock(spec=ssl.SSLContext)
    cfg = ClientConfiguration(url="https://example.invalid")
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        with (
            patch("kubex.client.httpx.httpx.AsyncClient") as mock_ac,
            patch(
                "kubex.client.httpx.ssl.create_default_context",
                return_value=fake_ssl_ctx,
            ) as mock_ctx,
        ):
            mock_ac.return_value = MagicMock()
            HttpxClient(
                cfg, ClientOptions(proxy="http://corp.proxy:8080", trust_env=True)
            )
    _, kwargs = mock_ac.call_args
    assert kwargs.get("trust_env") is False
    assert kwargs.get("verify") is fake_ssl_ctx
    mock_ctx.assert_called_once_with(cafile=None, capath="/path/to/cert/dir")


def test_trust_env_true_explicit_proxy_no_ssl_cert_file_keeps_bool_verify(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # When trust_env=True + explicit proxy but no SSL_CERT_FILE env var set,
    # our new SSL_CERT_FILE path is not triggered — verify stays as the bool
    # True that was set before the conflict branch runs. Use a config without
    # insecure_skip_tls_verify so needs_custom_ssl=False and _verify=True.
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    monkeypatch.delenv("SSL_CERT_DIR", raising=False)
    cfg = ClientConfiguration(url="https://example.invalid")
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        with patch("kubex.client.httpx.httpx.AsyncClient") as mock_ac:
            mock_ac.return_value = MagicMock()
            HttpxClient(
                cfg, ClientOptions(proxy="http://corp.proxy:8080", trust_env=True)
            )
    _, kwargs = mock_ac.call_args
    assert kwargs.get("trust_env") is False
    assert kwargs.get("verify") is True


def test_trust_env_true_no_explicit_proxy_invokes_env_resolver() -> None:
    fake_proxy = httpx.Proxy(url="http://proxy.corp:3128", auth=("alice", "s3cret"))
    resolver_result: dict[str, Any] = {"proxy": fake_proxy}
    with patch(
        "kubex.client.httpx._resolve_env_proxy_with_netrc",
        return_value=resolver_result,
    ) as mock_resolver:
        _, mock_ac = _patched_client(ClientOptions(trust_env=True))
    mock_resolver.assert_called_once_with("https://example.invalid")
    _, kwargs = mock_ac.call_args
    assert kwargs.get("proxy") == fake_proxy
    assert kwargs.get("trust_env") is True


def test_trust_env_true_explicit_proxy_dict_matching_scheme_emits_warning() -> None:
    # Dict proxy with a key matching the base URL scheme (https) conflicts with
    # trust_env=True → warning emitted and trust_env forced False (mirrors aiohttp).
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _, mock_ac = _patched_client(
            ClientOptions(proxy={"https": "http://corp.proxy:8080"}, trust_env=True)
        )
    _, kwargs = mock_ac.call_args
    assert any(
        issubclass(w.category, UserWarning)
        and "proxy" in str(w.message)
        and "trust_env" in str(w.message)
        for w in caught
    )
    assert kwargs.get("trust_env") is False


def test_trust_env_true_proxy_dict_no_matching_scheme_emits_warning() -> None:
    # Dict proxy only for http:// while the base URL is https:// — any explicit
    # proxy conflicts with trust_env=True regardless of scheme, so a warning is
    # emitted and trust_env is forced False. Mirrors the aiohttp backend.
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _, mock_ac = _patched_client(
            ClientOptions(proxy={"http": "http://corp.proxy:8080"}, trust_env=True)
        )
    _, kwargs = mock_ac.call_args
    assert any(
        issubclass(w.category, UserWarning)
        and "proxy" in str(w.message)
        and "trust_env" in str(w.message)
        for w in caught
    )
    assert kwargs.get("trust_env") is False
