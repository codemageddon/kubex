from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import TYPE_CHECKING, Any, AsyncGenerator, NoReturn, Sequence

if TYPE_CHECKING:
    from typing_extensions import Self

    from kubex.client.websocket import WebSocketConnection

from pydantic import ValidationError

from kubex.client.options import ClientOptions
from kubex.configuration import ClientConfiguration
from kubex.configuration.file_config import configure_from_kubeconfig
from kubex.configuration.incluster_config import configure_from_pod_env
from kubex.core.exceptions import build_exception
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


class ClientChoice(str, Enum):
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
    client_class: ClientChoice = ClientChoice.AUTO,
    options: ClientOptions | None = None,
) -> BaseClient:
    if options is not None and not isinstance(options, ClientOptions):
        raise TypeError(
            f"options must be a ClientOptions instance or None, got {type(options).__name__!r}"
        )
    if configuration is None:
        configuration = await _try_read_configuration()
    match client_class:
        case ClientChoice.HTTPX:
            from .httpx import HttpxClient

            return HttpxClient(configuration, options)
        case ClientChoice.AIOHTTP:
            from .aiohttp import AioHttpClient

            return AioHttpClient(configuration, options)
        case ClientChoice.AUTO:
            try:
                return await create_client(configuration, ClientChoice.AIOHTTP, options)
            except ImportError:
                try:
                    return await create_client(
                        configuration, ClientChoice.HTTPX, options
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
    raise build_exception(status_code, content)
