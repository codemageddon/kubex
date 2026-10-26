"""E2E tests for ``ClientOptions(proxy=...)`` with URL-embedded credentials (Squid + K3S).

Complements test_trust_env.py, which covers the env-var path: an explicit
proxy goes through kubex's own credential handling on aiohttp.
"""

from __future__ import annotations

import pytest

from kubex.api import Api
from kubex.client.client import ClientChoice, create_client
from kubex.client.options import ClientOptions
from kubex.configuration.configuration import ClientConfiguration
from kubex.core.exceptions import KubexClientException, KubexConnectionError
from kubex.k8s.v1_35.core.v1.namespace import Namespace
from kubex.k8s.v1_35.core.v1.pod import Pod
from test.e2e._helpers import create_busybox_pod, wait_for_pod_running
from test.e2e.proxy._constants import SQUID_PROXY_PASSWORD, SQUID_PROXY_USER

pytestmark = pytest.mark.anyio

_WRONG_PASSWORD = "wrong-proxy-password"


def _proxy_with(proxy_url: str, password: str) -> str:
    host_port = proxy_url.removeprefix("http://")
    return f"http://{SQUID_PROXY_USER}:{password}@{host_port}"


def _assert_no_password(exc: BaseException, password: str) -> None:
    current: BaseException | None = exc
    while current is not None:
        assert password not in str(current)
        current = current.__cause__


async def test_explicit_proxy_with_embedded_creds_succeeds(
    kubernetes_config_via_proxy: ClientConfiguration,
    proxy_url: str,
    client_choice: ClientChoice,
) -> None:
    async with await create_client(
        kubernetes_config_via_proxy,
        client_class=client_choice,
        options=ClientOptions(proxy=_proxy_with(proxy_url, SQUID_PROXY_PASSWORD)),
    ) as client:
        api: Api[Namespace] = Api(Namespace, client=client)
        result = await api.list()

    names = [ns.metadata.name for ns in result.items if ns.metadata]
    assert "default" in names


async def test_explicit_proxy_exec_with_embedded_creds_succeeds(
    kubernetes_config_via_proxy: ClientConfiguration,
    proxy_url: str,
    client_choice: ClientChoice,
    tmp_namespace_name_via_proxy: str,
) -> None:
    async with await create_client(
        kubernetes_config_via_proxy,
        client_class=client_choice,
        options=ClientOptions(proxy=_proxy_with(proxy_url, SQUID_PROXY_PASSWORD)),
    ) as client:
        api: Api[Pod] = Api(Pod, client=client, namespace=tmp_namespace_name_via_proxy)
        await create_busybox_pod(api, "explicit-proxy", tmp_namespace_name_via_proxy)
        await wait_for_pod_running(api, "explicit-proxy", tmp_namespace_name_via_proxy)
        result = await api.exec.run("explicit-proxy", command=["echo", "via-proxy"])

    assert result.stdout == b"via-proxy\n"
    assert result.exit_code == 0


async def test_explicit_proxy_wrong_creds_error_omits_password(
    kubernetes_config_via_proxy: ClientConfiguration,
    proxy_url: str,
    client_choice: ClientChoice,
) -> None:
    """Squid answers the CONNECT with 407; the error must not echo the proxy URL's password."""
    async with await create_client(
        kubernetes_config_via_proxy,
        client_class=client_choice,
        options=ClientOptions(proxy=_proxy_with(proxy_url, _WRONG_PASSWORD)),
    ) as client:
        api: Api[Namespace] = Api(Namespace, client=client)
        with pytest.raises(KubexConnectionError, match="407") as exc_info:
            await api.list()

    _assert_no_password(exc_info.value, _WRONG_PASSWORD)


async def test_explicit_proxy_exec_wrong_creds_error_omits_password(
    kubernetes_config_via_proxy: ClientConfiguration,
    proxy_url: str,
    client_choice: ClientChoice,
) -> None:
    async with await create_client(
        kubernetes_config_via_proxy,
        client_class=client_choice,
        options=ClientOptions(proxy=_proxy_with(proxy_url, _WRONG_PASSWORD)),
    ) as client:
        api: Api[Pod] = Api(Pod, client=client, namespace="default")
        with pytest.raises(KubexClientException, match="407") as exc_info:
            await api.exec.run("no-such-pod", command=["echo", "hi"])

    _assert_no_password(exc_info.value, _WRONG_PASSWORD)
