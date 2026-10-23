from __future__ import annotations

import json
import math
import ssl
from base64 import b64decode, b64encode, urlsafe_b64decode
from enum import Enum
from urllib.parse import urlencode

from pydantic import BaseModel, SecretStr

from kubex.configuration.configuration import OIDCConfig
from kubex.core.exceptions import ConfigurationError

_MISSING_HTTP_LIBRARY_MESSAGE = (
    "OIDC authentication requires aiohttp or httpx to be installed; "
    "install one with `pip install aiohttp` or `pip install httpx`"
)

# Matches ClientOptions' documented default (opt-in only) and gives both
# backends the same behaviour instead of httpx's trust_env=True/5s and
# aiohttp's trust_env=False/300s defaults.
_TRUST_ENV = False
_TIMEOUT_SECONDS = 30.0


def _build_ssl_context(
    idp_certificate_authority_data: str | None,
) -> ssl.SSLContext | None:
    """Build an SSLContext trusting only the kubeconfig-supplied IdP CA, if any.

    Mirrors the `certificate-authority-data` handling used for the main API
    server connection (`ssl.create_default_context(cafile=...)`), but the IdP
    CA arrives as in-memory base64 rather than a file, so it is passed via
    `cadata` instead of writing a temp file.
    """
    if idp_certificate_authority_data is None:
        return None
    pem = b64decode(idp_certificate_authority_data).decode("ascii")
    return ssl.create_default_context(cadata=pem)


def _oidc_error(operation: str, status: int, body: bytes) -> ConfigurationError:
    """Build a ConfigurationError describing a failed OIDC HTTP call.

    Surfaces the HTTP status and, when the body is a standard OAuth error
    JSON object, the `error`/`error_description` fields, rather than letting
    callers fail later on an unrelated `ValueError` or `JSONDecodeError`.
    """
    detail = ""
    try:
        parsed = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        parsed = None
    if isinstance(parsed, dict) and (
        "error" in parsed or "error_description" in parsed
    ):
        error = parsed.get("error", "")
        description = parsed.get("error_description", "")
        detail = f": {error} {description}".rstrip()
    return ConfigurationError(f"OIDC {operation} failed with HTTP {status}{detail}")


def _jwt_exp_claim(token: str) -> float | None:
    """Best-effort extraction of the `exp` claim (Unix epoch seconds) from a JWT payload.

    The signature is not verified: kubex trusts the TLS-authenticated token endpoint
    that issued the token, the same trust boundary client-go relies on for
    `oidcAuthProvider.idTokenExpired()`, which reads `exp` from the id_token itself
    rather than the token response's `expires_in` (that field describes the access
    token's lifetime, not the id_token's -- the two can differ significantly).
    """
    parts = token.split(".")
    if len(parts) != 3:
        return None
    payload = parts[1]
    padded = payload + "=" * (-len(payload) % 4)
    try:
        claims = json.loads(urlsafe_b64decode(padded))
    except (ValueError, UnicodeDecodeError):
        return None
    exp = claims.get("exp") if isinstance(claims, dict) else None
    if isinstance(exp, bool) or not isinstance(exp, int | float):
        return None
    try:
        exp = float(exp)
    except OverflowError:
        return None
    return exp if math.isfinite(exp) else None


class AuthStyle(Enum):
    HEADER = "header"
    PARAMS = "params"


class OidcMetadata(BaseModel):
    token_endpoint: str


OPEN_ID_DISCOVERY_URL = ".well-known/openid-configuration"


async def _get(
    url: str, headers: dict[str, str], ssl_context: ssl.SSLContext | None = None
) -> tuple[int, bytes]:
    """GET `url`, preferring httpx when installed and falling back to aiohttp.

    httpx works on both asyncio and trio; aiohttp is asyncio-only (it calls
    `asyncio.get_running_loop()` internally) and raises under trio regardless
    of which client the caller configured. httpx is therefore tried first so
    OIDC auth doesn't silently break trio applications that also happen to
    have aiohttp installed (e.g. any `--all-extras` install). Either optional
    HTTP extra installed alone is still enough to use OIDC authentication.
    """
    try:
        import httpx
    except ImportError:
        pass
    else:
        async with httpx.AsyncClient(
            verify=ssl_context if ssl_context is not None else True,
            trust_env=_TRUST_ENV,
            timeout=_TIMEOUT_SECONDS,
        ) as client:
            httpx_response = await client.get(url, headers=headers)
            return httpx_response.status_code, httpx_response.content
    try:
        import aiohttp
    except ImportError as exc:
        raise ConfigurationError(_MISSING_HTTP_LIBRARY_MESSAGE) from exc
    async with aiohttp.ClientSession(
        trust_env=_TRUST_ENV,
        timeout=aiohttp.ClientTimeout(total=_TIMEOUT_SECONDS),
    ) as session:
        async with session.get(
            url, headers=headers, ssl=ssl_context if ssl_context is not None else True
        ) as response:
            return response.status, await response.read()


async def _post_form(
    url: str,
    headers: dict[str, str],
    body: str,
    ssl_context: ssl.SSLContext | None = None,
) -> tuple[int, bytes]:
    """POST a pre-encoded form `body` to `url`, same backend preference as `_get()`."""
    try:
        import httpx
    except ImportError:
        pass
    else:
        async with httpx.AsyncClient(
            verify=ssl_context if ssl_context is not None else True,
            trust_env=_TRUST_ENV,
            timeout=_TIMEOUT_SECONDS,
        ) as client:
            httpx_response = await client.post(url, headers=headers, content=body)
            return httpx_response.status_code, httpx_response.content
    try:
        import aiohttp
    except ImportError as exc:
        raise ConfigurationError(_MISSING_HTTP_LIBRARY_MESSAGE) from exc
    async with aiohttp.ClientSession(
        trust_env=_TRUST_ENV,
        timeout=aiohttp.ClientTimeout(total=_TIMEOUT_SECONDS),
    ) as session:
        async with session.post(
            url,
            headers=headers,
            data=body.encode(),
            ssl=ssl_context if ssl_context is not None else True,
        ) as response:
            return response.status, await response.read()


class OIDCAuthProvider:
    def __init__(self, config: OIDCConfig):
        self.config = config
        self._token_endpoint: str | None = None
        self._auth_style: AuthStyle | None = None
        self._ssl_context = _build_ssl_context(config.idp_certificate_authority_data)

    async def _discover(self) -> str:
        if self._token_endpoint is not None:
            return self._token_endpoint
        issuer_url = self.config.idp_issuer_url.rstrip("/")
        status, content = await _get(
            f"{issuer_url}/{OPEN_ID_DISCOVERY_URL}",
            headers={"Accept": "application/json"},
            ssl_context=self._ssl_context,
        )
        if not (200 <= status < 300):
            raise _oidc_error("discovery", status, content)
        metadata = OidcMetadata.model_validate_json(content)
        if not metadata.token_endpoint.startswith("https://"):
            raise ConfigurationError(
                "OIDC discovery returned a non-https token_endpoint "
                f"({metadata.token_endpoint!r}); refusing to send credentials to it"
            )
        self._token_endpoint = metadata.token_endpoint
        return self._token_endpoint

    async def _id_token(self) -> bytes:
        token_endpoint = await self._discover()
        if self._auth_style is not None:
            headers, body = self._token_request(self._auth_style)
            status, content = await _post_form(
                token_endpoint, headers, body, ssl_context=self._ssl_context
            )
            if not (200 <= status < 300):
                raise _oidc_error("token request", status, content)
            return content
        last_status = 0
        last_content = b""
        for auth_style in AuthStyle:
            headers, body = self._token_request(auth_style)
            status, content = await _post_form(
                token_endpoint, headers, body, ssl_context=self._ssl_context
            )
            if 200 <= status < 300:
                self._auth_style = auth_style
                return content
            last_status, last_content = status, content
        raise _oidc_error("token request", last_status, last_content)

    def _basic_auth(self) -> str:
        credentials = f"{self.config.client_id.get_secret_value()}:{self.config.client_secret.get_secret_value()}"
        return b64encode(credentials.encode()).decode()

    def _token_request(self, auth_style: AuthStyle) -> tuple[dict[str, str], str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        if auth_style == AuthStyle.HEADER:
            headers["Authorization"] = f"Basic {self._basic_auth()}"
            body = urlencode(
                [
                    ("grant_type", "refresh_token"),
                    ("refresh_token", self.config.refresh_token.get_secret_value()),
                ],
            )
        else:
            body = urlencode(
                [
                    ("grant_type", "refresh_token"),
                    ("refresh_token", self.config.refresh_token.get_secret_value()),
                    ("client_id", self.config.client_id.get_secret_value()),
                    ("client_secret", self.config.client_secret.get_secret_value()),
                ],
            )
        return headers, body

    async def refresh_token(self) -> tuple[str, float | None]:
        """Fetch a fresh id_token, rotating the in-memory refresh token if the IdP issues a new one.

        Returns the id_token and its own `exp` claim (Unix epoch seconds), if it is a
        decodable JWT carrying one. This is deliberately not the token response's
        `expires_in` field, which describes the access token's lifetime -- a
        separate token with its own, independently configured expiry -- not the
        id_token that kubex actually sends to the API server.

        A rotated refresh token is kept only on `self.config` for the life of this
        process; it is not written back to the source kubeconfig file. Against an
        IdP configured for refresh-token rotation (e.g. Auth0, Okta, Keycloak with
        rotation enabled), the on-disk kubeconfig's refresh token is single-use and
        is invalidated by the first successful refresh, so a fresh process (or a
        concurrent `kubectl` using the same kubeconfig) must re-authenticate
        interactively once this token has been used here.
        """
        content = await self._id_token()
        data = json.loads(content)
        id_token = data.get("id_token")
        if not isinstance(id_token, str):
            raise ValueError("OIDC: id_token not found in token response")
        rotated_refresh_token = data.get("refresh_token")
        if isinstance(rotated_refresh_token, str) and rotated_refresh_token:
            self.config.refresh_token = SecretStr(rotated_refresh_token)
        return id_token, _jwt_exp_claim(id_token)
