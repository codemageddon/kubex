import ssl
import warnings
from typing import Any, AsyncGenerator

from aiohttp import ClientSession, ClientTimeout
from aiohttp.connector import TCPConnector

from kubex.configuration import ClientConfiguration
from kubex.core.params import Timeout
from kubex.core.request import Request
from kubex.core.request_builder import constants
from kubex.core.response import HeadersWrapper, Response

from .client import (
    BaseClient,
    handle_request_error,
)


def _to_aiohttp_timeout(timeout: Timeout | None) -> ClientTimeout:
    """Translate a ``Timeout`` (or explicit ``None``) to ``ClientTimeout``.

    ``write`` and ``pool`` are ignored: aiohttp does not support them.
    """
    if timeout is None:
        return ClientTimeout(total=None)
    return ClientTimeout(
        total=timeout.total,
        sock_connect=timeout.connect,
        sock_read=timeout.read,
    )


class AioHttpClient(BaseClient):
    def __init__(self, configuration: ClientConfiguration) -> None:
        self._configuration = configuration
        self._default_headers = {
            constants.CONTENT_TYPE_HEADER: constants.APPLICATION_JSON_MIME_TYPE,
            constants.ACCEPT_HEADER: constants.APPLICATION_JSON_MIME_TYPE,
        }
        self._inner_client: ClientSession = self._create_inner_client()

    @property
    def configuration(self) -> ClientConfiguration:
        return self._configuration

    def _get_headers(self) -> dict[str, str]:
        if self.configuration.token is None:
            return {}
        return {"Authorization": f"Bearer {self.configuration.token}"}

    def _create_inner_client(self) -> ClientSession:
        ssl_context = ssl.create_default_context(
            cafile=self.configuration.server_ca_file
        )
        if (client_cert := self.configuration.client_cert) is not None:
            if isinstance(client_cert, tuple):
                ssl_context.load_cert_chain(
                    certfile=client_cert[0], keyfile=client_cert[1]
                )
            else:
                ssl_context.load_cert_chain(certfile=client_cert)

        if self.configuration.insecure_skip_tls_verify:
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

        connector = TCPConnector(
            verify_ssl=not bool(self.configuration.insecure_skip_tls_verify),
            ssl=ssl_context,
        )
        kwargs: dict[str, Any] = {
            "base_url": str(self.configuration.base_url),
            "connector": connector,
            "read_bufsize": 2**21,
            "headers": self._default_headers,
        }
        configured_timeout = self.configuration.timeout
        if configured_timeout is not Ellipsis:
            kwargs["timeout"] = _to_aiohttp_timeout(configured_timeout)
        return ClientSession(**kwargs)

    async def request(self, request: Request) -> Response:
        headers = self._get_headers()
        if request.headers:
            headers.update(request.headers)
        extra: dict[str, Any] = {}
        if request.timeout is not Ellipsis:
            extra["timeout"] = _to_aiohttp_timeout(request.timeout)
        _response = await self._inner_client.request(
            method=request.method,
            url=request.url,
            params=request.query_params,
            data=request.body,
            headers=headers,
            **extra,
        )
        status = _response.status
        response = Response(
            status_code=status,
            headers=HeadersWrapper(_response.headers),
            content=await _response.read(),
        )
        if self.configuration.log_api_warnings and (
            api_warnings := _response.headers.get("Warning")
        ):
            for warning in api_warnings.split(","):
                warnings.warn(f"API Warning: {warning}")
        if 400 <= status < 600:
            handle_request_error(response)
        return response

    async def stream_lines(self, request: Request) -> AsyncGenerator[str, None]:
        headers = self._get_headers()
        if request.headers:
            headers.update(request.headers)
        extra: dict[str, Any] = {}
        if request.timeout is not Ellipsis:
            extra["timeout"] = _to_aiohttp_timeout(request.timeout)
        _response = await self._inner_client.request(
            method=request.method,
            url=request.url,
            params=request.query_params,
            data=request.body,
            headers=headers,
            **extra,
        )
        status = _response.status
        if 400 <= status < 600:
            response = Response(
                status_code=status,
                headers=HeadersWrapper(_response.headers),
                content=await _response.read(),
            )
            handle_request_error(response)
        while line := await _response.content.readline():
            yield line.decode("utf-8")

    async def close(self) -> None:
        await self._inner_client.close()
