from __future__ import annotations

import builtins
import json
import ssl
from base64 import b64encode, urlsafe_b64encode
from typing import Any
from unittest.mock import AsyncMock

import httpx
import pytest
from pydantic import SecretStr

from kubex.configuration.auth.oidc import (
    OIDCAuthProvider,
    _build_ssl_context,
    _get,
    _jwt_exp_claim,
    _post_form,
)
from kubex.configuration.configuration import OIDCConfig
from kubex.core.exceptions import ConfigurationError


@pytest.fixture
def anyio_backend() -> str:
    # asyncio only: the aiohttp-fallback test below constructs a real
    # aiohttp.ClientSession, which aiohttp itself does not support under trio.
    return "asyncio"


def _oidc_config() -> OIDCConfig:
    return OIDCConfig(
        client_id=SecretStr("client-id"),
        client_secret=SecretStr("client-secret"),
        refresh_token=SecretStr("initial-refresh"),
        idp_issuer_url="https://issuer.example.com",
    )


def _fake_jwt(payload: dict[str, Any]) -> str:
    """Build an unsigned `header.payload.signature`-shaped JWT for testing exp extraction."""

    def _segment(data: dict[str, Any]) -> str:
        return urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()

    return f"{_segment({'alg': 'none'})}.{_segment(payload)}.signature"


def test_jwt_exp_claim_reads_exp() -> None:
    token = _fake_jwt({"exp": 1_700_000_000, "sub": "user"})
    assert _jwt_exp_claim(token) == 1_700_000_000.0


def test_jwt_exp_claim_returns_none_without_exp() -> None:
    token = _fake_jwt({"sub": "user"})
    assert _jwt_exp_claim(token) is None


def test_jwt_exp_claim_returns_none_for_non_jwt_string() -> None:
    assert _jwt_exp_claim("not-a-jwt") is None


def test_jwt_exp_claim_rejects_boolean() -> None:
    token = _fake_jwt({"exp": True})
    assert _jwt_exp_claim(token) is None


def test_jwt_exp_claim_rejects_nan_and_infinity() -> None:
    assert _jwt_exp_claim(_fake_jwt({"exp": float("nan")})) is None
    assert _jwt_exp_claim(_fake_jwt({"exp": float("inf")})) is None


def test_jwt_exp_claim_rejects_overflowing_integer() -> None:
    token = _fake_jwt({"exp": 10**400})
    assert _jwt_exp_claim(token) is None


def test_build_ssl_context_returns_none_without_ca_data() -> None:
    assert _build_ssl_context(None) is None


def test_build_ssl_context_decodes_base64_and_builds_from_pem(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pem = "-----BEGIN CERTIFICATE-----\nfake-ca-cert\n-----END CERTIFICATE-----\n"
    encoded = b64encode(pem.encode()).decode()
    captured: dict[str, Any] = {}

    def _fake_create_default_context(*, cadata: str) -> ssl.SSLContext:
        captured["cadata"] = cadata
        return ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

    monkeypatch.setattr(ssl, "create_default_context", _fake_create_default_context)

    context = _build_ssl_context(encoded)

    assert isinstance(context, ssl.SSLContext)
    assert captured["cadata"] == pem


def test_provider_builds_ssl_context_from_config_ca_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    monkeypatch.setattr(
        "kubex.configuration.auth.oidc._build_ssl_context", lambda _data: sentinel
    )
    config = _oidc_config()
    config.idp_certificate_authority_data = "irrelevant-because-monkeypatched"

    provider = OIDCAuthProvider(config)

    assert provider._ssl_context is sentinel


@pytest.mark.anyio
async def test_discover_passes_provider_ssl_context_to_get(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    provider = OIDCAuthProvider(_oidc_config())
    provider._ssl_context = sentinel
    captured: dict[str, Any] = {}

    async def _fake_get(
        url: str, headers: dict[str, str], ssl_context: ssl.SSLContext | None = None
    ) -> tuple[int, bytes]:
        captured["ssl_context"] = ssl_context
        return 200, b'{"token_endpoint": "https://issuer.example.com/token"}'

    monkeypatch.setattr("kubex.configuration.auth.oidc._get", _fake_get)

    await provider._discover()

    assert captured["ssl_context"] is sentinel


@pytest.mark.anyio
async def test_id_token_passes_provider_ssl_context_to_post_form(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    provider = OIDCAuthProvider(_oidc_config())
    provider._ssl_context = sentinel
    provider._token_endpoint = "https://issuer.example.com/token"
    captured: dict[str, Any] = {}

    async def _fake_post_form(
        url: str,
        headers: dict[str, str],
        body: str,
        ssl_context: ssl.SSLContext | None = None,
    ) -> tuple[int, bytes]:
        captured["ssl_context"] = ssl_context
        return 200, b'{"id_token": "irrelevant"}'

    monkeypatch.setattr("kubex.configuration.auth.oidc._post_form", _fake_post_form)

    await provider._id_token()

    assert captured["ssl_context"] is sentinel


@pytest.mark.anyio
async def test_refresh_token_rotates_refresh_token() -> None:
    provider = OIDCAuthProvider(_oidc_config())
    id_token = _fake_jwt({"exp": 1_700_000_000})
    provider._id_token = AsyncMock(  # type: ignore[method-assign]
        return_value=json.dumps(
            {"id_token": id_token, "refresh_token": "rotated-refresh"}
        ).encode()
    )

    returned_token, exp_claim = await provider.refresh_token()

    assert returned_token == id_token
    assert exp_claim == 1_700_000_000.0
    assert provider.config.refresh_token.get_secret_value() == "rotated-refresh"


@pytest.mark.anyio
async def test_refresh_token_keeps_original_when_response_has_no_rotation() -> None:
    provider = OIDCAuthProvider(_oidc_config())
    provider._id_token = AsyncMock(  # type: ignore[method-assign]
        return_value=b'{"id_token": "new-id"}'
    )

    id_token, exp_claim = await provider.refresh_token()

    # "new-id" isn't a decodable JWT, so no exp claim is available.
    assert exp_claim is None
    assert provider.config.refresh_token.get_secret_value() == "initial-refresh"


@pytest.mark.anyio
async def test_refresh_token_raises_without_id_token() -> None:
    provider = OIDCAuthProvider(_oidc_config())
    provider._id_token = AsyncMock(return_value=b"{}")  # type: ignore[method-assign]

    with pytest.raises(ValueError, match="id_token not found"):
        await provider.refresh_token()


@pytest.mark.anyio
async def test_get_raises_configuration_error_without_aiohttp_or_httpx(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_import = builtins.__import__

    def _blocking_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name in ("aiohttp", "httpx"):
            raise ImportError("blocked for test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _blocking_import)
    provider = OIDCAuthProvider(_oidc_config())

    with pytest.raises(ConfigurationError, match="aiohttp or httpx"):
        await provider._discover()


@pytest.mark.anyio
async def test_get_prefers_httpx_over_aiohttp_when_both_installed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """httpx works on both asyncio and trio; aiohttp is asyncio-only and raises
    under trio regardless of which client backend the caller configured. httpx
    must be tried first so OIDC auth doesn't silently break trio applications
    that also happen to have aiohttp installed (e.g. any --all-extras install).
    """

    async def _fake_get(
        self: httpx.AsyncClient, url: str, headers: dict[str, str] | None = None
    ) -> httpx.Response:
        return httpx.Response(200, content=b"ok")

    def _aiohttp_should_not_be_used(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("aiohttp should not be used when httpx is available")

    monkeypatch.setattr(httpx.AsyncClient, "get", _fake_get)
    monkeypatch.setattr(
        "aiohttp.ClientSession.get", _aiohttp_should_not_be_used, raising=False
    )

    status, content = await _get("https://issuer.example.com/discovery", {})

    assert status == 200
    assert content == b"ok"


class _FakeAiohttpResponse:
    status = 200

    async def read(self) -> bytes:
        return b"ok-aiohttp"


class _FakeAiohttpRequestCM:
    async def __aenter__(self) -> _FakeAiohttpResponse:
        return _FakeAiohttpResponse()

    async def __aexit__(self, *exc_info: Any) -> None:
        return None


@pytest.mark.anyio
async def test_post_form_falls_back_to_aiohttp_without_httpx(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import aiohttp

    real_import = builtins.__import__

    def _blocking_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "httpx":
            raise ImportError("blocked for test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _blocking_import)
    monkeypatch.setattr(
        aiohttp.ClientSession,
        "post",
        lambda self, url, headers=None, data=None, ssl=None: _FakeAiohttpRequestCM(),
    )

    status, content = await _post_form(
        "https://issuer.example.com/token", {}, "grant_type=refresh_token"
    )

    assert status == 200
    assert content == b"ok-aiohttp"
