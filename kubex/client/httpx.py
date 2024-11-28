from __future__ import annotations

import warnings
from http import HTTPStatus
from typing import AsyncGenerator

import httpx

from kubex.configuration import ClientConfiguration
from kubex.core.request import Request
from kubex.core.response import HeadersWrapper, Response

from .client import (
    BaseClient,
    handle_request_error,
)


class HttpxClient(BaseClient):
    def __init__(self, configuration: ClientConfiguration) -> None:
        self._configuration = configuration
        self._inner_client = self._create_inner_client()

    @property
    def configuration(self) -> ClientConfiguration:
        return self._configuration

    def _get_headers(self) -> dict[str, str]:
        if self.configuration.token is None:
            return {}
        return {"Authorization": f"Bearer {self.configuration.token}"}

    def _create_inner_client(self) -> httpx.AsyncClient:
        _verify: bool | str = True
        verify = self.configuration.verify
        if verify is False:
            _verify = False
        elif verify is None:
            _verify = True
        else:
            _verify = verify

        return httpx.AsyncClient(
            base_url=str(self.configuration.base_url),
            verify=_verify,
            cert=self.configuration.client_cert,
        )

    async def request(self, request: Request) -> Response:
        headers = self._get_headers()
        if request.headers:
            headers.update(request.headers)
        _response = await self._inner_client.request(
            method=request.method,
            url=request.url,
            params=request.query_params,
            content=request.body,
            headers=headers,
        )
        http_status = HTTPStatus(_response.status_code)
        response = Response(
            status_code=http_status,
            headers=HeadersWrapper(_response.headers),
            content=_response.content,
        )
        if self.configuration.log_api_warnings and (
            api_warnings := _response.headers.get("warning")
        ):
            for warning in api_warnings.split(","):
                warnings.warn(f"API Warning: {warning}")
        if http_status.is_client_error or http_status.is_server_error:
            handle_request_error(response)
        return response

    async def stream_lines(self, request: Request) -> AsyncGenerator[str, None]:
        headers = self._get_headers()
        if request.headers:
            headers.update(request.headers)
        async with self._inner_client.stream(
            method=request.method,
            url=request.url,
            params=request.query_params,
            content=request.body,
            headers=headers,
        ) as _response:
            http_status = HTTPStatus(_response.status_code)
            if http_status.is_client_error or http_status.is_server_error:
                response = Response(
                    status_code=_response.status_code,
                    headers=HeadersWrapper(_response.headers),
                    content=await _response.aread(),
                )
                handle_request_error(response)
            async for line in _response.aiter_lines():
                yield line

    async def close(self) -> None:
        await self._inner_client.aclose()
