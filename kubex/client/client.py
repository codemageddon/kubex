from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import TYPE_CHECKING, Any, AsyncGenerator, NoReturn, Self, Sequence

if TYPE_CHECKING:
    from kubex.client.websocket import WebSocketConnection

from pydantic import ValidationError

from kubex.client._common import parse_retry_after
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

_RETRY_AFTER = "Retry-After"


async def _try_read_configuration() -> ClientConfiguration:
    try:
        return await configure_from_kubeconfig()
    except FileNotFoundError:
        logger.debug("No kubeconfig file found, falling back to in-cluster config")
        return await configure_from_pod_env()
    except Exception:
        # No exception text: kubeconfig validation errors can embed credentials.
        logger.debug("Failed to read configuration from kubeconfig")
        raise


def _running_under_asyncio() -> bool:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return False
    return True


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

    @property
    def configuration(self) -> ClientConfiguration:
        return self._configuration

    @abstractmethod
    def _create_inner_client(self) -> Any: ...

    async def _request_headers(self, request: Request) -> list[tuple[str, str]]:
        """Auth + impersonation + per-request headers, as (possibly repeated) pairs.

        A header set on the request replaces the client-level header of the same
        name.
        """
        explicit = request.headers or {}
        overridden = {name.lower() for name in explicit}
        headers: list[tuple[str, str]] = []
        if "authorization" not in overridden:
            authorization = await self.configuration.get_authorization_header()
            if authorization is not None:
                headers.append(("Authorization", authorization))
        headers.extend(
            (name, value)
            for name, value in self.configuration.impersonation_headers
            if name.lower() not in overridden
        )
        headers.extend(explicit.items())
        return headers

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
            if not _running_under_asyncio():
                # aiohttp is asyncio-only; under trio (or any other runtime)
                # only httpx can work.
                try:
                    return await create_client(
                        configuration, ClientChoice.HTTPX, options
                    )
                except ImportError:
                    raise ImportError(
                        "You need to install httpx to use the client outside asyncio"
                    )
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
    # An error body from an intermediary (proxy, gateway) is not guaranteed to
    # be UTF-8 or JSON; `Response.text` decodes tolerantly.
    content: Status | str = response.text
    if content_types := response.headers.get_all(CONTENT_TYPE_HEADER):
        if any(ct.startswith(APPLICATION_JSON_MIME_TYPE) for ct in content_types):
            try:
                status = Status.model_validate_json(response.content)
            except ValidationError:
                pass
            else:
                # Any JSON object validates (all Status fields are optional);
                # keep the raw text for bodies that are not a Status at all.
                if "kind" in status.model_fields_set:
                    content = status
    retry_after = parse_retry_after(
        next(iter(response.headers.get_all(_RETRY_AFTER)), None)
    )
    raise build_exception(status_code, content, retry_after=retry_after)
