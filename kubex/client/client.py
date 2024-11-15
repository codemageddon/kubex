from __future__ import annotations

import logging
import warnings
from http import HTTPStatus
from types import TracebackType
from typing import AsyncGenerator, NoReturn, Self

import httpx
from pydantic import ValidationError

from kubex.client.configuration import ClientConfiguration
from kubex.core import exceptions
from kubex.core.request import Request
from kubex.core.request_builder.constants import (
    APPLICATION_JSON_MIME_TYPE,
    CONTENT_TYPE_HEADER,
)
from kubex.core.response import Response
from kubex.models.status import Status

from .file_config import configure_from_kubeconfig
from .incluster_config import configure_from_pod_env

logger = logging.getLogger("kubex.client")


async def _try_read_configuration() -> ClientConfiguration:
    try:
        return await configure_from_kubeconfig()
    except Exception as e:
        logger.error("Failed to read configuration from kubeconfig", exc_info=e)
        return await configure_from_pod_env()


class Client:
    def __init__(self, configuration: ClientConfiguration) -> None:
        self._configuration = configuration
        self._inner_client = self._create_inner_client()

    @classmethod
    async def create(cls, configuration: ClientConfiguration | None = None) -> Self:
        if configuration is None:
            configuration = await _try_read_configuration()
        self = cls(configuration)
        return self

    @property
    def configuration(self) -> ClientConfiguration:
        return self._configuration

    def _get_headers(self) -> dict[str, str]:
        if self.configuration.token is None:
            return {}
        return {"Authorization": f"Bearer {self.configuration.token}"}

    def _create_inner_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=str(self.configuration.base_url),
            verify=self.configuration.verify,
            cert=self.configuration.client_cert,
        )

    async def __aenter__(self) -> Self:
        await self._inner_client.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: TracebackType | None = None,
    ) -> None:
        await self._inner_client.__aexit__(exc_type, exc_value, traceback)

    def handle_request_error(self, response: Response) -> NoReturn:
        status_code = response.status_code
        content: Status | str
        if CONTENT_TYPE_HEADER in response.headers:
            content_type = response.headers[CONTENT_TYPE_HEADER]
            if content_type == APPLICATION_JSON_MIME_TYPE:
                try:
                    content = Status.model_validate_json(response.content)
                except ValidationError:
                    content = response.text
            else:
                content = response.text
        match status_code:
            case HTTPStatus.BAD_REQUEST:
                raise exceptions.BadRequest(content=content)
            case HTTPStatus.UNAUTHORIZED:
                raise exceptions.Unauthorized(content=content)
            case HTTPStatus.FORBIDDEN:
                raise exceptions.Forbidden(content=content)
            case HTTPStatus.NOT_FOUND:
                raise exceptions.NotFound(content=content)
            case HTTPStatus.METHOD_NOT_ALLOWED:
                raise exceptions.MethodNotAllowed(content=content)
            case HTTPStatus.CONFLICT:
                raise exceptions.Conflict(content=content)
            case HTTPStatus.GONE:
                raise exceptions.Gone(content=content)
            case HTTPStatus.UNPROCESSABLE_ENTITY:
                raise exceptions.UnprocessableEntity(content=content)
            case status:
                raise exceptions.KubexApiError(
                    content=content, status=HTTPStatus(status)
                )
        raise exceptions.KubernetesError(content=content)

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
            headers=_response.headers,
            content=_response.content,
        )
        if self.configuration.log_api_warnings and (
            api_warnings := _response.headers.get("Warning")
        ):
            for warning in api_warnings.split(","):
                warnings.warn(f"API Warning: {warning}")
        if http_status.is_client_error or http_status.is_server_error:
            self.handle_request_error(response)
        return response

    async def stream_lines(self, request: Request) -> AsyncGenerator[str, None]:
        async with self._inner_client.stream(
            method=request.method,
            url=request.url,
            params=request.query_params,
            content=request.body,
            headers=request.headers,
        ) as _response:
            http_status = HTTPStatus(_response.status_code)
            if http_status.is_client_error or http_status.is_server_error:
                response = Response(
                    status_code=_response.status_code,
                    headers=_response.headers,
                    content=await _response.aread(),
                )
                self.handle_request_error(response)
            async for line in _response.aiter_lines():
                yield line

    async def close(self) -> None:
        await self._inner_client.aclose()
