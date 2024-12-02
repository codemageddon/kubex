from base64 import b64encode
from enum import Enum
from urllib.parse import urlencode

from httpx import AsyncClient
from pydantic import BaseModel

from kubex.configuration.configuration import OIDCConfig
from kubex.core.request import Request
from kubex.core.response import Response


class AuthStyle(Enum):
    HEADER = "header"
    PARAMS = "params"


class OidcMetadata(BaseModel):
    token_endpoint: str


OPEN_ID_DISCOVERY_URL = ".well-known/openid-configuration"


class OIDCAuthProvider:
    def __init__(self, config: OIDCConfig):
        self.config = config
        self._token_endpoint: str | None = None
        self._auth_style: AuthStyle | None = None

    def _client(self) -> AsyncClient:
        return AsyncClient(
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )

    async def _discover(self) -> str:
        if self._token_endpoint is not None:
            return self._token_endpoint
        async with self._client() as client:
            response = await client.get(
                f"{self.config.idp_issuer_url}/{OPEN_ID_DISCOVERY_URL}"
            )
            metadata = OidcMetadata.model_validate_json(response.content)
        self._token_endpoint = metadata.token_endpoint
        return self._token_endpoint

    async def _id_token(self) -> Response:
        token_endpoint = await self._discover()
        if self._auth_style is not None:
            request = await self._token_request(token_endpoint, self._auth_style)
            async with self._client() as client:
                response = await client.post(request)
                return response
        else:
            for auth_style in AuthStyle:
                request = await self._token_request(token_endpoint, auth_style)
                ok_response = None
                async with self._client() as client:
                    response = await client.send(request)
                    if 300 < response.status_code >= 200:
                        ok_response = response
                        self._auth_style = auth_style
                        break
            return ok_response

    def _basic_auth(self) -> str:
        credentials = f"{self.config.client_id.get_secret_value()}:{self.config.client_secret.get_secret_value()}"
        return b64encode(credentials.encode()).decode()

    async def _token_request(
        self, token_endpoint: str, auth_style: AuthStyle
    ) -> Request:
        if auth_style == AuthStyle.HEADER:
            return Request(
                method="POST",
                url=token_endpoint,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "authorization": f"Basic {self._basic_auth()}",
                },
                body=urlencode(
                    [
                        ("grant_type", "refresh_token"),
                        ("refresh_token", self.config.refresh_token.get_secret_value()),
                    ],
                ),
            )
        return Request(
            method="POST",
            url=token_endpoint,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            body=urlencode(
                [
                    ("grant_type", "refresh_token"),
                    ("refresh_token", self.config.refresh_token.get_secret_value()),
                    ("client_id", self.config.client_id.get_secret_value()),
                    ("client_secret", self.config.client_secret.get_secret_value()),
                ],
            ),
        )

    async def refresh_token(self) -> str:
        raise NotImplementedError()
