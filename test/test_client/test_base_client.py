from __future__ import annotations

import warnings
from unittest.mock import AsyncMock, patch

import pytest

from kubex.client.options import ClientOptions
from kubex.configuration import ClientConfiguration

httpx = pytest.importorskip("httpx")

from kubex.client.httpx import HttpxClient  # noqa: E402


def _config() -> ClientConfiguration:
    return ClientConfiguration(
        url="https://example.invalid", insecure_skip_tls_verify=True
    )


def test_base_client_defaults_options_when_none() -> None:
    client = HttpxClient(_config())
    assert isinstance(client.options, ClientOptions)
    assert client.options.timeout is Ellipsis
    assert client.options.log_api_warnings is True


def test_base_client_stores_explicit_options() -> None:
    opts = ClientOptions(log_api_warnings=False, timeout=10)
    client = HttpxClient(_config(), opts)
    assert client.options is opts


@pytest.mark.anyio
async def test_log_api_warnings_true_emits_warning() -> None:
    client = HttpxClient(_config(), ClientOptions(log_api_warnings=True))
    fake_response = httpx.Response(
        status_code=200,
        headers={"warning": "299 - deprecated"},
        content=b"{}",
    )
    with patch.object(
        client._inner_client, "request", new=AsyncMock(return_value=fake_response)
    ):
        from kubex.core.request import Request

        req = Request(method="GET", url="/api/v1/pods", query_params={})
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            await client.request(req)
        assert any(
            issubclass(w.category, UserWarning) and "deprecated" in str(w.message)
            for w in caught
        )


@pytest.mark.anyio
async def test_log_api_warnings_false_suppresses_warning() -> None:
    client = HttpxClient(_config(), ClientOptions(log_api_warnings=False))
    fake_response = httpx.Response(
        status_code=200,
        headers={"warning": "299 - deprecated"},
        content=b"{}",
    )
    with patch.object(
        client._inner_client, "request", new=AsyncMock(return_value=fake_response)
    ):
        from kubex.core.request import Request

        req = Request(method="GET", url="/api/v1/pods", query_params={})
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            await client.request(req)
        assert not any(
            issubclass(w.category, UserWarning) and "API Warning" in str(w.message)
            for w in caught
        )
