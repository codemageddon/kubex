from __future__ import annotations

import pytest

from kubex.client.options import ClientOptions
from kubex.configuration import ClientConfiguration
from kubex.core.params import Timeout

httpx = pytest.importorskip("httpx")

from kubex.client.httpx import HttpxClient, _to_httpx_timeout  # noqa: E402


def _configuration() -> ClientConfiguration:
    return ClientConfiguration(
        url="https://example.invalid",
        insecure_skip_tls_verify=True,
    )


def test_create_inner_client_without_timeout_uses_httpx_default() -> None:
    client = HttpxClient(_configuration())
    assert client._inner_client.timeout == httpx.Timeout(5.0)


def test_create_inner_client_with_timeout() -> None:
    client = HttpxClient(_configuration(), ClientOptions(timeout=5))
    assert client._inner_client.timeout == httpx.Timeout(5.0)


def test_create_inner_client_with_none_disables_timeout() -> None:
    client = HttpxClient(_configuration(), ClientOptions(timeout=None))
    assert client._inner_client.timeout == httpx.Timeout(None)


def test_to_httpx_timeout_translates_granular_fields() -> None:
    translated = _to_httpx_timeout(Timeout(total=5, connect=1, read=2, write=3, pool=4))
    assert translated == httpx.Timeout(5.0, connect=1, read=2, write=3, pool=4)


def test_to_httpx_timeout_none_means_disabled() -> None:
    translated = _to_httpx_timeout(None)
    assert translated == httpx.Timeout(None)


@pytest.mark.parametrize(
    ("client_timeout", "expected"),
    [
        pytest.param(
            ..., httpx.Timeout(None, connect=5.0, write=5.0, pool=5.0), id="default"
        ),
        pytest.param(
            Timeout(total=30),
            httpx.Timeout(None, connect=30.0, write=30.0, pool=30.0),
            id="total",
        ),
        pytest.param(
            Timeout(connect=2, read=60),
            httpx.Timeout(None, connect=2.0),
            id="connect-read",
        ),
        pytest.param(None, httpx.Timeout(None), id="disabled"),
    ],
)
def test_stream_timeout_keeps_connection_bounds_and_drops_read(
    client_timeout: object, expected: object
) -> None:
    # Watches and log follows idle legitimately; only connection setup is
    # bounded by the client default.
    client = HttpxClient(_configuration(), ClientOptions(timeout=client_timeout))
    assert client._stream_timeout() == expected
