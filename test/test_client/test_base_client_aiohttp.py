from __future__ import annotations

import warnings
from unittest.mock import AsyncMock, patch

import pytest

from kubex.client.options import ClientOptions
from kubex.configuration import ClientConfiguration

pytest.importorskip("aiohttp")

from multidict import CIMultiDict  # noqa: E402

from kubex.client.aiohttp import AioHttpClient  # noqa: E402


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _config() -> ClientConfiguration:
    return ClientConfiguration(
        url="https://example.invalid", insecure_skip_tls_verify=True
    )


@pytest.mark.anyio
async def test_aiohttp_log_api_warnings_true_emits_warning() -> None:
    client = AioHttpClient(_config(), ClientOptions(log_api_warnings=True))
    mock_response_obj = type(
        "FakeResp",
        (),
        {
            "status": 200,
            "headers": CIMultiDict({"warning": "299 - deprecated"}),
            "read": AsyncMock(return_value=b"{}"),
        },
    )()
    with patch.object(
        client._inner_client, "request", new=AsyncMock(return_value=mock_response_obj)
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
async def test_aiohttp_log_api_warnings_false_suppresses_warning() -> None:
    client = AioHttpClient(_config(), ClientOptions(log_api_warnings=False))
    mock_response_obj = type(
        "FakeResp",
        (),
        {
            "status": 200,
            "headers": CIMultiDict({"warning": "299 - deprecated"}),
            "read": AsyncMock(return_value=b"{}"),
        },
    )()
    with patch.object(
        client._inner_client, "request", new=AsyncMock(return_value=mock_response_obj)
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
