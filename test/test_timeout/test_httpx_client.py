from __future__ import annotations

import pytest

from kubex.configuration import ClientConfiguration
from kubex.core.params import Timeout

httpx = pytest.importorskip("httpx")

from kubex.client.httpx import HttpxClient, _to_httpx_timeout  # noqa: E402


def _configuration(**kwargs: object) -> ClientConfiguration:
    return ClientConfiguration(
        url="https://example.invalid",
        insecure_skip_tls_verify=True,
        **kwargs,  # type: ignore[arg-type]
    )


def test_create_inner_client_without_timeout_uses_httpx_default() -> None:
    client = HttpxClient(_configuration())
    # Constructing without a timeout should leave httpx's default in place.
    assert client._inner_client.timeout == httpx.Timeout(5.0)


def test_create_inner_client_with_timeout() -> None:
    client = HttpxClient(_configuration(timeout=5))
    assert client._inner_client.timeout == httpx.Timeout(5.0)


def test_create_inner_client_with_none_disables_timeout() -> None:
    client = HttpxClient(_configuration(timeout=None))
    assert client._inner_client.timeout == httpx.Timeout(None)


def test_to_httpx_timeout_translates_granular_fields() -> None:
    translated = _to_httpx_timeout(Timeout(total=5, connect=1, read=2, write=3, pool=4))
    assert translated == httpx.Timeout(5.0, connect=1, read=2, write=3, pool=4)


def test_to_httpx_timeout_none_means_disabled() -> None:
    translated = _to_httpx_timeout(None)
    assert translated == httpx.Timeout(None)
