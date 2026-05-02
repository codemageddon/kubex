from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from enum import Enum
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, AsyncGenerator, NoReturn, Sequence

if TYPE_CHECKING:
    from typing_extensions import Self

    from kubex.client.websocket import WebSocketConnection

from pydantic import ValidationError

from kubex.client.options import ClientOptions
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
from kubex_core.models.status import Status

logger = logging.getLogger("kubex.client")


async def _try_read_configuration() -> ClientConfiguration:
    try:
        return await configure_from_kubeconfig()
    except FileNotFoundError:
        logger.debug("No kubeconfig file found, falling back to in-cluster config")
        return await configure_from_pod_env()
    except Exception as e:
        logger.error("Failed to read configuration from kubeconfig", exc_info=e)
        raise


class ClientChoise(str, Enum):
    HTTPX = "httpx"
    AIOHTTP = "aiohttp"
    AUTO = "auto"


class BaseClient(ABC):
    def __init__(
        self,
        configuration: ClientConfiguration,
        options: ClientOptions | None = None,
    ) -> None:
        super().__init__()
        self._configuration = configuration
        self._options = options if options is not None else ClientOptions()
        self._inner_client: Any = self._create_inner_client()

    @property
    def options(self) -> ClientOptions:
        return self._options

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

    async def connect_websocket(
        self,
        request: Request,
        subprotocols: Sequence[str],
    ) -> "WebSocketConnection":
        """Open a WebSocket connection for a streaming subresource.

        .. warning::

           **Experimental.** The WebSocket transport (used by ``exec``,
           ``attach`` and ``portforward``) is still under active development
           and the surrounding API may change in future releases without
           notice.
        """
        raise NotImplementedError("WebSocket not supported by this client")


async def create_client(
    configuration: ClientConfiguration | None = None,
    options: ClientOptions | None = None,
    client_class: ClientChoise = ClientChoise.AUTO,
) -> BaseClient:
    if options is not None and not isinstance(options, ClientOptions):
        raise TypeError(
            f"options must be a ClientOptions instance or None, got {type(options).__name__!r}"
        )
    if configuration is None:
        configuration = await _try_read_configuration()
    match client_class:
        case ClientChoise.HTTPX:
            from .httpx import HttpxClient

            return HttpxClient(configuration, options)
        case ClientChoise.AIOHTTP:
            from .aiohttp import AioHttpClient

            return AioHttpClient(configuration, options)
        case ClientChoise.AUTO:
            try:
                return await create_client(configuration, options, ClientChoise.AIOHTTP)
            except ImportError:
                try:
                    return await create_client(
                        configuration, options, ClientChoise.HTTPX
                    )
                except ImportError:
                    raise ImportError(
                        "You need to install either httpx or aiohttp to use the client"
                    )


def handle_request_error(response: Response) -> NoReturn:
    status_code = response.status_code
    content: Status | str = response.text
    if content_types := response.headers.get_all(CONTENT_TYPE_HEADER):
        if any(ct.startswith(APPLICATION_JSON_MIME_TYPE) for ct in content_types):
            try:
                content = Status.model_validate_json(response.content)
            except ValidationError:
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
            try:
                http_status = HTTPStatus(status)
            except ValueError:
                http_status = HTTPStatus.INTERNAL_SERVER_ERROR
            raise exceptions.KubexApiError(content=content, status=http_status)
