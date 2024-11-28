from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from enum import Enum
from http import HTTPStatus
from typing import Any, AsyncGenerator, NoReturn, Self

from pydantic import ValidationError

from kubex.configuration import ClientConfiguration
from kubex.configuration.file_config import configure_from_kubeconfig
from kubex.configuration.incluster_config import configure_from_pod_env
from kubex.core import exceptions
from kubex.core.request import Request
from kubex.core.request_builder.constants import (
    APPLICATION_JSON_MIME_TYPE,
    CONTENT_TYPE_HEADER,
)
from kubex.core.response import Response
from kubex.models.status import Status

logger = logging.getLogger("kubex.client")


async def _try_read_configuration() -> ClientConfiguration:
    try:
        return await configure_from_kubeconfig()
    except Exception as e:
        logger.error("Failed to read configuration from kubeconfig", exc_info=e)
        return await configure_from_pod_env()


class ClientChoise(str, Enum):
    HTTPX = "httpx"
    AIOHTTP = "aiohttp"
    AUTO = "auto"


class BaseClient(ABC):
    def __init__(self, configuration: ClientConfiguration) -> None:
        super().__init__()
        self._configuration = configuration
        self._inner_client: Any = self._create_inner_client()

    @abstractmethod
    def _create_inner_client(self) -> Any: ...

    async def __aenter__(self) -> Self:
        await self._inner_client.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: Any | None = None,
    ) -> None:
        await self._inner_client.__aexit__(exc_type, exc_value, traceback)

    @abstractmethod
    async def request(self, request: Request) -> Response:
        pass

    @abstractmethod
    def stream_lines(self, request: Request) -> AsyncGenerator[str, None]:
        pass

    @abstractmethod
    async def close(self) -> None:
        pass


async def create_client(
    configuration: ClientConfiguration | None = None,
    client_class: ClientChoise = ClientChoise.AUTO,
) -> BaseClient:
    if configuration is None:
        configuration = await _try_read_configuration()
    match client_class:
        case ClientChoise.HTTPX:
            from .httpx import HttpxClient

            return HttpxClient(configuration)
        case ClientChoise.AIOHTTP:
            from .aiohttp import AioHttpClient

            return AioHttpClient(configuration)
        case ClientChoise.AUTO:
            try:
                return await create_client(configuration, ClientChoise.HTTPX)
            except ImportError:
                try:
                    return await create_client(configuration, ClientChoise.AIOHTTP)
                except ImportError:
                    raise ImportError(
                        "You need to install either httpx or aiohttp to use the client"
                    )


def handle_request_error(response: Response) -> NoReturn:
    status_code = response.status_code
    content: Status | str
    if content_types := response.headers.get_all(CONTENT_TYPE_HEADER):
        if APPLICATION_JSON_MIME_TYPE in content_types:
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
            raise exceptions.KubexApiError(content=content, status=HTTPStatus(status))
    raise exceptions.KubernetesError(content=content)
