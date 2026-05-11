"""E2E tests for trust_env with a Squid forward proxy and K3S.

These tests validate the canonical HTTPS_PROXY + ~/.netrc flow on both backends
using a Squid forward proxy on a shared Docker network with K3S.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from kubex.api import Api
from kubex.client.client import ClientChoise, create_client
from kubex.client.options import ClientOptions
from kubex.configuration.configuration import ClientConfiguration
from kubex.core.exceptions import KubexClientException, Unauthorized
from kubex.k8s.v1_35.core.v1.namespace import Namespace
from kubex.k8s.v1_35.core.v1.pod import Pod
from test.e2e._helpers import create_busybox_pod, wait_for_pod_running
from test.e2e.proxy._constants import SQUID_PROXY_PASSWORD, SQUID_PROXY_USER

pytestmark = pytest.mark.anyio


async def test_trust_env_proxy_url_with_embedded_creds_succeeds(
    kubernetes_config_via_proxy: ClientConfiguration,
    proxy_url: str,
    client_choice: ClientChoise,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """HTTPS_PROXY with embedded user:pass succeeds — no netrc lookup needed."""
    host_port = proxy_url.removeprefix("http://")
    monkeypatch.setenv(
        "HTTPS_PROXY", f"http://{SQUID_PROXY_USER}:{SQUID_PROXY_PASSWORD}@{host_port}"
    )

    async with await create_client(
        kubernetes_config_via_proxy,
        client_class=client_choice,
        options=ClientOptions(trust_env=True),
    ) as client:
        api: Api[Namespace] = Api(Namespace, client=client)
        result = await api.list()

    assert result is not None
    names = [ns.metadata.name for ns in result.items if ns.metadata]
    assert "default" in names


async def test_trust_env_proxy_creds_from_netrc_succeeds(
    kubernetes_config_via_proxy: ClientConfiguration,
    proxy_url: str,
    proxy_netrc: Path,
    client_choice: ClientChoise,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """HTTPS_PROXY without creds + netrc with creds succeeds.

    Exercises _resolve_env_proxy_with_netrc on httpx and aiohttp's native netrc.
    """
    monkeypatch.setenv("HTTPS_PROXY", proxy_url)
    monkeypatch.setenv("NETRC", str(proxy_netrc))

    async with await create_client(
        kubernetes_config_via_proxy,
        client_class=client_choice,
        options=ClientOptions(trust_env=True),
    ) as client:
        api: Api[Namespace] = Api(Namespace, client=client)
        result = await api.list()

    assert result is not None
    names = [ns.metadata.name for ns in result.items if ns.metadata]
    assert "default" in names


async def test_trust_env_proxy_missing_creds_fails(
    kubernetes_config_via_proxy: ClientConfiguration,
    proxy_url: str,
    client_choice: ClientChoise,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """HTTPS_PROXY without creds and no netrc -> proxy auth fails.

    Proves proxy authentication actually flows through the wire. Transport-level
    407 surfaces as httpx.ProxyError or aiohttp.ClientHttpProxyError (neither is
    KubexClientException) because BaseClient.request() does not wrap
    transport-level exceptions from the CONNECT tunnel.
    """
    monkeypatch.setenv("HTTPS_PROXY", proxy_url)
    # Point NETRC at a guaranteed-nonexistent path so the resolver cannot fall
    # back to ~/.netrc on the runner's machine (FileNotFoundError is caught and
    # treated as "no creds", which is the isolation we want here).
    monkeypatch.setenv("NETRC", str(tmp_path / "kubex_no_netrc"))

    with pytest.raises(Exception):
        async with await create_client(
            kubernetes_config_via_proxy,
            client_class=client_choice,
            options=ClientOptions(trust_env=True),
        ) as client:
            api: Api[Namespace] = Api(Namespace, client=client)
            await api.list()


async def test_no_proxy_bypasses_proxy(
    kubernetes_config_via_proxy: ClientConfiguration,
    proxy_url: str,
    client_choice: ClientChoise,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """NO_PROXY=k3s bypasses the proxy -> direct connection fails with DNS error.

    The docker-network alias "k3s" is not resolvable from the host, so the
    direct connection attempt raises a DNS/connection error. httpx raises
    httpx.ConnectError; aiohttp raises aiohttp.ClientConnectorError. Neither is
    KubexClientException because BaseClient.request() does not wrap
    transport-level exceptions.
    """
    monkeypatch.setenv("HTTPS_PROXY", proxy_url)
    monkeypatch.setenv("NO_PROXY", "k3s")

    with pytest.raises(Exception):
        async with await create_client(
            kubernetes_config_via_proxy,
            client_class=client_choice,
            options=ClientOptions(trust_env=True),
        ) as client:
            api: Api[Namespace] = Api(Namespace, client=client)
            await api.list()


async def test_trust_env_bearer_token_via_proxy_succeeds(
    kubernetes_token_config_via_proxy: ClientConfiguration,
    proxy_url: str,
    client_choice: ClientChoise,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SA bearer token + proxy basic auth: api.list() succeeds end-to-end.

    The Authorization: Bearer header travels inside the CONNECT tunnel and is
    invisible to the proxy.
    """
    host_port = proxy_url.removeprefix("http://")
    monkeypatch.setenv(
        "HTTPS_PROXY", f"http://{SQUID_PROXY_USER}:{SQUID_PROXY_PASSWORD}@{host_port}"
    )

    async with await create_client(
        kubernetes_token_config_via_proxy,
        client_class=client_choice,
        options=ClientOptions(trust_env=True),
    ) as client:
        result = await Api(Namespace, client=client).list()

    assert result is not None
    names = [ns.metadata.name for ns in result.items if ns.metadata]
    assert "default" in names


async def test_trust_env_bearer_invalid_token_returns_unauthorized(
    kubernetes_token_config_via_proxy: ClientConfiguration,
    proxy_url: str,
    client_choice: ClientChoise,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A garbage token survives the proxy tunnel and is rejected by K8s as 401."""
    host_port = proxy_url.removeprefix("http://")
    monkeypatch.setenv(
        "HTTPS_PROXY", f"http://{SQUID_PROXY_USER}:{SQUID_PROXY_PASSWORD}@{host_port}"
    )
    kubernetes_token_config_via_proxy._token = "not.a.valid.jwt"

    async with await create_client(
        kubernetes_token_config_via_proxy,
        client_class=client_choice,
        options=ClientOptions(trust_env=True),
    ) as client:
        with pytest.raises(Unauthorized):
            await Api(Namespace, client=client).list()


async def test_trust_env_exec_via_proxy_succeeds(
    kubernetes_config_via_proxy: ClientConfiguration,
    proxy_url: str,
    client_choice: ClientChoise,
    tmp_namespace_name_via_proxy: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """WebSocket exec via Squid with URL-embedded proxy creds succeeds."""
    host_port = proxy_url.removeprefix("http://")
    monkeypatch.setenv(
        "HTTPS_PROXY", f"http://{SQUID_PROXY_USER}:{SQUID_PROXY_PASSWORD}@{host_port}"
    )

    async with await create_client(
        kubernetes_config_via_proxy,
        client_class=client_choice,
        options=ClientOptions(trust_env=True),
    ) as client:
        api: Api[Pod] = Api(Pod, client=client, namespace=tmp_namespace_name_via_proxy)
        await create_busybox_pod(api, "ws-exec-cert", tmp_namespace_name_via_proxy)
        await wait_for_pod_running(api, "ws-exec-cert", tmp_namespace_name_via_proxy)
        result = await api.exec.run("ws-exec-cert", command=["echo", "ws-proxy"])

    assert result.stdout == b"ws-proxy\n"
    assert result.exit_code == 0


async def test_trust_env_exec_bearer_token_via_proxy_succeeds(
    kubernetes_admin_token_config_via_proxy: ClientConfiguration,
    proxy_url: str,
    client_choice: ClientChoise,
    tmp_namespace_name_via_proxy: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """WebSocket exec with SA bearer token via Squid proxy succeeds.

    Uses an admin-role SA token so the bearer token has permission to create pods
    and run exec. The Authorization: Bearer header travels inside the CONNECT
    tunnel and is invisible to the proxy; the proxy sees only Proxy-Authorization
    on the outer CONNECT line.
    """
    host_port = proxy_url.removeprefix("http://")
    monkeypatch.setenv(
        "HTTPS_PROXY", f"http://{SQUID_PROXY_USER}:{SQUID_PROXY_PASSWORD}@{host_port}"
    )

    async with await create_client(
        kubernetes_admin_token_config_via_proxy,
        client_class=client_choice,
        options=ClientOptions(trust_env=True),
    ) as client:
        api: Api[Pod] = Api(Pod, client=client, namespace=tmp_namespace_name_via_proxy)
        await create_busybox_pod(api, "ws-exec-bearer", tmp_namespace_name_via_proxy)
        await wait_for_pod_running(api, "ws-exec-bearer", tmp_namespace_name_via_proxy)
        result = await api.exec.run(
            "ws-exec-bearer", command=["echo", "ws-proxy-bearer"]
        )

    assert result.stdout == b"ws-proxy-bearer\n"
    assert result.exit_code == 0


async def test_trust_env_exec_missing_proxy_creds_fails(
    kubernetes_config_via_proxy: ClientConfiguration,
    proxy_url: str,
    client_choice: ClientChoise,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """HTTPS_PROXY without creds and no netrc -> proxy auth fails for WS exec.

    The proxy rejects the CONNECT tunnel with 407 before the WS handshake reaches
    the kubelet; no pod needs to exist. Both httpx and aiohttp backends wrap the
    transport failure as KubexClientException.
    """
    monkeypatch.setenv("HTTPS_PROXY", proxy_url)
    monkeypatch.setenv("NETRC", str(tmp_path / "kubex_no_netrc"))

    with pytest.raises(KubexClientException, match="407"):
        async with await create_client(
            kubernetes_config_via_proxy,
            client_class=client_choice,
            options=ClientOptions(trust_env=True),
        ) as client:
            api: Api[Pod] = Api(Pod, client=client, namespace="default")
            await api.exec.run("no-such-pod", command=["echo", "hi"])


async def test_trust_env_exec_no_proxy_bypasses_proxy(
    kubernetes_config_via_proxy: ClientConfiguration,
    proxy_url: str,
    client_choice: ClientChoise,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """NO_PROXY=k3s bypasses the proxy -> direct WS connect to k3s alias fails.

    The docker-network alias "k3s" is not resolvable from the host, so the
    direct connection attempt raises a DNS/connection error before the WS
    handshake reaches the kubelet. No pod needs to exist. Both httpx and aiohttp
    backends wrap the transport failure as KubexClientException.
    """
    host_port = proxy_url.removeprefix("http://")
    monkeypatch.setenv(
        "HTTPS_PROXY", f"http://{SQUID_PROXY_USER}:{SQUID_PROXY_PASSWORD}@{host_port}"
    )
    monkeypatch.setenv("NO_PROXY", "k3s")

    with pytest.raises(KubexClientException, match="connection failed"):
        async with await create_client(
            kubernetes_config_via_proxy,
            client_class=client_choice,
            options=ClientOptions(trust_env=True),
        ) as client:
            api: Api[Pod] = Api(Pod, client=client, namespace="default")
            await api.exec.run("no-such-pod", command=["echo", "hi"])
