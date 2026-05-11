from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

pytest.importorskip("httpx")

import httpx  # noqa: E402

from kubex.client.httpx import _getenv_icase, _resolve_env_proxy_with_netrc  # noqa: E402

_BASE_HTTPS = "https://apiserver.example.invalid:6443"
_BASE_HTTP = "http://apiserver.example.invalid:6443"
_PROXY_URL = "http://proxy.corp:3128"


@pytest.fixture(autouse=True)
def clean_proxy_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in [
        "http_proxy",
        "HTTP_PROXY",
        "https_proxy",
        "HTTPS_PROXY",
        "all_proxy",
        "ALL_PROXY",
        "no_proxy",
        "NO_PROXY",
        "NETRC",
    ]:
        monkeypatch.delenv(var, raising=False)


def test_resolve_env_proxy_with_netrc_no_env_var() -> None:
    result = _resolve_env_proxy_with_netrc(_BASE_HTTPS)
    assert result == {}


def test_resolve_env_proxy_with_netrc_url_has_creds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proxy = "http://user:pw@host:3128"
    monkeypatch.setenv("HTTPS_PROXY", proxy)
    result = _resolve_env_proxy_with_netrc(_BASE_HTTPS)
    assert result == {"proxy": proxy}


def test_resolve_env_proxy_with_netrc_lookup(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HTTPS_PROXY", _PROXY_URL)
    netrc_file = tmp_path / "netrc"
    netrc_file.write_text("machine proxy.corp login alice password s3cret\n")
    monkeypatch.setenv("NETRC", str(netrc_file))

    result = _resolve_env_proxy_with_netrc(_BASE_HTTPS)

    proxy = result.get("proxy")
    assert isinstance(proxy, httpx.Proxy)
    assert proxy.auth == ("alice", "s3cret")
    assert proxy.url.host == "proxy.corp"
    assert proxy.url.port == 3128


def test_resolve_env_proxy_with_netrc_ipv6_host(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HTTPS_PROXY", "http://[::1]:3128")
    netrc_file = tmp_path / "netrc"
    netrc_file.write_text("machine ::1 login alice password s3cret\n")
    monkeypatch.setenv("NETRC", str(netrc_file))

    result = _resolve_env_proxy_with_netrc(_BASE_HTTPS)

    proxy = result.get("proxy")
    assert isinstance(proxy, httpx.Proxy)
    assert proxy.auth == ("alice", "s3cret")


def test_resolve_env_proxy_with_netrc_null_password(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # netrc.authenticators() returns password=None when the password field is
    # absent. The code coerces it to "" via `password or ""` so httpx.Proxy
    # receives a valid (login, "") tuple rather than (login, None).
    monkeypatch.setenv("HTTPS_PROXY", _PROXY_URL)
    netrc_file = tmp_path / "netrc"
    netrc_file.write_text("machine proxy.corp login alice\n")
    monkeypatch.setenv("NETRC", str(netrc_file))

    result = _resolve_env_proxy_with_netrc(_BASE_HTTPS)

    proxy = result.get("proxy")
    assert isinstance(proxy, httpx.Proxy)
    assert proxy.auth == ("alice", "")


def test_resolve_env_proxy_with_netrc_no_matching_entry(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HTTPS_PROXY", _PROXY_URL)
    netrc_file = tmp_path / "netrc"
    netrc_file.write_text("machine other.host login user password pass\n")
    monkeypatch.setenv("NETRC", str(netrc_file))

    result = _resolve_env_proxy_with_netrc(_BASE_HTTPS)
    assert result == {"proxy": _PROXY_URL}


def test_resolve_env_proxy_scheme_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HTTP_PROXY", "http://http-proxy.corp:3128")
    monkeypatch.setenv("HTTPS_PROXY", "http://https-proxy.corp:3128")

    result = _resolve_env_proxy_with_netrc(_BASE_HTTPS)
    assert result == {"proxy": "http://https-proxy.corp:3128"}


def test_resolve_env_proxy_lowercase_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("https_proxy", "http://proxy.corp:3128")

    result = _resolve_env_proxy_with_netrc(_BASE_HTTPS)
    assert result == {"proxy": "http://proxy.corp:3128"}


def test_resolve_env_proxy_lowercase_wins_over_uppercase(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("https_proxy", "http://low.proxy:3128")
    monkeypatch.setenv("HTTPS_PROXY", "http://up.proxy:3128")

    result = _resolve_env_proxy_with_netrc(_BASE_HTTPS)
    assert result == {"proxy": "http://low.proxy:3128"}


def test_resolve_env_proxy_all_proxy_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALL_PROXY", "http://all-proxy.corp:3128")

    https_result = _resolve_env_proxy_with_netrc(_BASE_HTTPS)
    http_result = _resolve_env_proxy_with_netrc(_BASE_HTTP)
    assert https_result == {"proxy": "http://all-proxy.corp:3128"}
    assert http_result == {"proxy": "http://all-proxy.corp:3128"}


def test_resolve_env_proxy_no_proxy_exact_host(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HTTPS_PROXY", _PROXY_URL)
    monkeypatch.setenv("NO_PROXY", "apiserver.test")

    result = _resolve_env_proxy_with_netrc("https://apiserver.test")
    assert result == {}


def test_resolve_env_proxy_no_proxy_suffix_match(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HTTPS_PROXY", _PROXY_URL)
    monkeypatch.setenv("NO_PROXY", ".example.com")

    result = _resolve_env_proxy_with_netrc("https://api.example.com")
    assert result == {}


def test_resolve_env_proxy_no_proxy_bare_domain_matches_subdomains(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HTTPS_PROXY", _PROXY_URL)
    monkeypatch.setenv("NO_PROXY", "example.com")

    result = _resolve_env_proxy_with_netrc("https://api.example.com")
    assert result == {}


def test_resolve_env_proxy_no_proxy_no_match(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HTTPS_PROXY", _PROXY_URL)
    monkeypatch.setenv("NO_PROXY", ".example.com")

    result = _resolve_env_proxy_with_netrc("https://api.other.com")
    assert result == {"proxy": _PROXY_URL}


def test_resolve_env_proxy_no_proxy_ip_literal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HTTPS_PROXY", _PROXY_URL)
    monkeypatch.setenv("NO_PROXY", "10.0.0.5")

    result = _resolve_env_proxy_with_netrc("https://10.0.0.5:6443")
    assert result == {}


def test_resolve_env_proxy_no_proxy_ip_no_cidr_support(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HTTPS_PROXY", _PROXY_URL)
    monkeypatch.setenv("NO_PROXY", "10.0.0.0/24")

    result = _resolve_env_proxy_with_netrc("https://10.0.0.5:6443")
    assert result == {"proxy": _PROXY_URL}


def test_resolve_env_proxy_no_proxy_comma_separated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HTTPS_PROXY", _PROXY_URL)
    monkeypatch.setenv("NO_PROXY", "foo.com, .example.com, 10.0.0.5")

    result = _resolve_env_proxy_with_netrc("https://api.example.com")
    assert result == {}


def test_resolve_env_proxy_no_proxy_wildcard_all(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HTTPS_PROXY", _PROXY_URL)
    monkeypatch.setenv("NO_PROXY", "*")

    result = _resolve_env_proxy_with_netrc(_BASE_HTTPS)
    assert result == {}


def test_resolve_env_proxy_no_proxy_leading_dot_matches_domain_itself(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HTTPS_PROXY", _PROXY_URL)
    monkeypatch.setenv("NO_PROXY", ".example.com")

    result = _resolve_env_proxy_with_netrc("https://example.com:6443")
    assert result == {}


def test_resolve_env_proxy_no_proxy_entry_with_port_not_supported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Port-qualified NO_PROXY entries (e.g. "example.com:6443") are NOT
    # supported — consistent with Python stdlib / aiohttp behavior.
    # Use a bare hostname entry ("example.com") instead.
    monkeypatch.setenv("HTTPS_PROXY", _PROXY_URL)
    monkeypatch.setenv("NO_PROXY", "example.com:6443")

    result = _resolve_env_proxy_with_netrc("https://example.com:6443")
    assert result == {"proxy": _PROXY_URL}


def test_resolve_env_proxy_no_proxy_bare_ipv6_matches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HTTPS_PROXY", _PROXY_URL)
    monkeypatch.setenv("NO_PROXY", "::1")

    result = _resolve_env_proxy_with_netrc("https://[::1]:6443")
    assert result == {}


def test_resolve_env_proxy_no_proxy_bracketed_ipv6_not_supported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Bracketed IPv6 (e.g. [::1]) in NO_PROXY is NOT supported — consistent
    # with Python stdlib and aiohttp which do not strip brackets.
    # Use the bare form (::1) instead.
    monkeypatch.setenv("HTTPS_PROXY", _PROXY_URL)
    monkeypatch.setenv("NO_PROXY", "[::1]")

    result = _resolve_env_proxy_with_netrc("https://[::1]:6443")
    assert result == {"proxy": _PROXY_URL}


def test_resolve_env_proxy_no_proxy_bracketed_ipv6_with_port_not_supported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # [::1]:6443 in NO_PROXY is not supported (port qualifier + bracketed IPv6).
    monkeypatch.setenv("HTTPS_PROXY", _PROXY_URL)
    monkeypatch.setenv("NO_PROXY", "[::1]:6443")

    result = _resolve_env_proxy_with_netrc("https://[::1]:6443")
    assert result == {"proxy": _PROXY_URL}


def test_resolve_env_proxy_netrc_parse_error_falls_back(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HTTPS_PROXY", _PROXY_URL)
    netrc_file = tmp_path / "netrc"
    netrc_file.write_text("not a valid netrc file content\n")
    monkeypatch.setenv("NETRC", str(netrc_file))

    result = _resolve_env_proxy_with_netrc(_BASE_HTTPS)
    assert result == {"proxy": _PROXY_URL}


@pytest.mark.skipif(
    sys.platform == "win32" or (hasattr(os, "getuid") and os.getuid() == 0),
    reason="chmod not reliable on Windows or as root",
)
def test_resolve_env_proxy_netrc_unreadable_falls_back(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HTTPS_PROXY", _PROXY_URL)
    netrc_file = tmp_path / "netrc"
    netrc_file.write_text("machine proxy.corp login alice password s3cret\n")
    netrc_file.chmod(0o000)
    monkeypatch.setenv("NETRC", str(netrc_file))

    result = _resolve_env_proxy_with_netrc(_BASE_HTTPS)
    assert result == {"proxy": _PROXY_URL}


def test_resolve_env_proxy_empty_lowercase_suppresses_uppercase(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("https_proxy", "")
    monkeypatch.setenv("HTTPS_PROXY", _PROXY_URL)

    result = _resolve_env_proxy_with_netrc(_BASE_HTTPS)
    assert result == {}


def test_resolve_env_proxy_empty_lowercase_does_not_suppress_all_proxy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Empty https_proxy suppresses HTTPS_PROXY but should still fall through
    # to ALL_PROXY, matching urllib.request.getproxies_environment() semantics.
    monkeypatch.setenv("https_proxy", "")
    monkeypatch.setenv("ALL_PROXY", "http://all-proxy.corp:3128")

    result = _resolve_env_proxy_with_netrc(_BASE_HTTPS)
    assert result == {"proxy": "http://all-proxy.corp:3128"}


def test_resolve_env_proxy_cgi_safeguard_skips_uppercase_http_proxy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("REQUEST_METHOD", "GET")
    monkeypatch.setenv("HTTP_PROXY", _PROXY_URL)

    result = _resolve_env_proxy_with_netrc(_BASE_HTTP)
    assert result == {}


def test_resolve_env_proxy_cgi_safeguard_allows_lowercase_http_proxy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("REQUEST_METHOD", "GET")
    monkeypatch.setenv("http_proxy", _PROXY_URL)

    result = _resolve_env_proxy_with_netrc(_BASE_HTTP)
    assert result == {"proxy": _PROXY_URL}


def test_resolve_env_proxy_no_proxy_empty_lowercase_suppresses_uppercase(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HTTPS_PROXY", _PROXY_URL)
    monkeypatch.setenv("no_proxy", "")
    monkeypatch.setenv("NO_PROXY", "apiserver.example.invalid")

    result = _resolve_env_proxy_with_netrc(_BASE_HTTPS)
    assert result == {"proxy": _PROXY_URL}


def test_resolve_env_proxy_mixed_case_proxy_var_picks_up_netrc(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Mixed-case env var (e.g. Https_Proxy) must be picked up so kubex can
    # attach netrc creds — without this, httpx uses the proxy natively but
    # skips netrc enrichment, causing 407 auth failures.
    monkeypatch.setenv("Https_Proxy", _PROXY_URL)
    netrc_file = tmp_path / "netrc"
    netrc_file.write_text("machine proxy.corp login alice password s3cret\n")
    monkeypatch.setenv("NETRC", str(netrc_file))

    result = _resolve_env_proxy_with_netrc(_BASE_HTTPS)

    proxy = result.get("proxy")
    assert isinstance(proxy, httpx.Proxy)
    assert proxy.auth == ("alice", "s3cret")


def test_resolve_env_proxy_mixed_case_no_proxy_bypasses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Mixed-case No_Proxy must still bypass the proxy.  Without case-insensitive
    # lookup, the resolver materialises an explicit proxy= kwarg and httpx never
    # gets a chance to apply the bypass.
    monkeypatch.setenv("HTTPS_PROXY", _PROXY_URL)
    monkeypatch.setenv("No_Proxy", "apiserver.example.invalid")

    result = _resolve_env_proxy_with_netrc(_BASE_HTTPS)
    assert result == {}


def test_getenv_icase_returns_actual_stored_key_not_normalized_lookup_form(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # _getenv_icase must return the key exactly as stored in os.environ,
    # not the lowercase form used for the lookup.  On Windows, os.environ is
    # case-insensitive, so ``"http_proxy" in os.environ`` matches a stored
    # ``HTTP_PROXY`` entry and would cause _getenv_icase to return the
    # synthetic lowercase key — breaking the HTTPOXY guard which compares
    # ``found_key == "HTTP_PROXY"``.
    monkeypatch.setenv("HTTP_PROXY", _PROXY_URL)
    key, val = _getenv_icase("http_proxy")
    assert key == "HTTP_PROXY"
    assert val == _PROXY_URL


def test_getenv_icase_lowercase_key_returned_as_is(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("https_proxy", _PROXY_URL)
    key, val = _getenv_icase("https_proxy")
    assert key == "https_proxy"
    assert val == _PROXY_URL


def test_getenv_icase_missing_returns_none_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    key, val = _getenv_icase("https_proxy")
    assert key is None
    assert val == ""
