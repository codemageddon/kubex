from __future__ import annotations

import pytest

from kubex.api import Api
from kubex.client.client import BaseClient, ClientChoise, create_client
from kubex.configuration.configuration import ClientConfiguration
from kubex.core.exceptions import Unauthorized
from kubex.k8s.v1_35.core.v1.namespace import Namespace

pytestmark = pytest.mark.anyio


async def test_bearer_token_succeeds(token_client: BaseClient) -> None:
    result = await Api(Namespace, client=token_client).list()
    assert result is not None
    names = [ns.metadata.name for ns in result.items if ns.metadata]
    assert "default" in names


async def test_bearer_invalid_token_returns_unauthorized(
    kubernetes_token_config: ClientConfiguration,
    client_choice: ClientChoise,
) -> None:
    kubernetes_token_config._token = "not.a.valid.jwt"
    async with await create_client(
        kubernetes_token_config, client_class=client_choice
    ) as client:
        with pytest.raises(Unauthorized):
            await Api(Namespace, client=client).list()
