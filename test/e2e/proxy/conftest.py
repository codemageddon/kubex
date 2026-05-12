from __future__ import annotations

import shlex
import stat
from pathlib import Path
from typing import AsyncGenerator, Generator
from urllib.parse import urlparse

import pytest
from testcontainers.core.container import DockerContainer  # type: ignore[import-untyped]
from testcontainers.core.network import Network  # type: ignore[import-untyped]
from testcontainers.core.waiting_utils import wait_for_logs  # type: ignore[import-untyped]
from testcontainers.k3s import K3SContainer  # type: ignore[import-untyped]
from yaml import safe_load

from kubex.api import Api
from kubex.client.httpx import HttpxClient
from kubex.configuration.configuration import ClientConfiguration, KubeConfig
from kubex.configuration.file_config import configure_from_kubeconfig
from kubex.k8s.v1_35.core.v1.namespace import Namespace
from kubex_core.models.metadata import ObjectMetadata
from test.e2e._helpers import mint_sa_token
from test.e2e.proxy._constants import SQUID_PROXY_PASSWORD, SQUID_PROXY_USER

# Heredoc delimiter chosen to be unlikely to appear in the config body.
_SQUID_CONF_HEREDOC = "KUBEX_SQUID_CONF_EOF"

_SQUID_CONF = """\
auth_param basic program /usr/lib/squid/basic_ncsa_auth /etc/squid/passwords
auth_param basic realm kubex-proxy-test
acl authenticated proxy_auth REQUIRED
acl k3s_port port 6443
acl CONNECT method CONNECT
http_access allow CONNECT k3s_port authenticated
http_access deny all
http_port 3128
access_log none
cache deny all
"""


@pytest.fixture(scope="session")
def proxy_network() -> Generator[Network, None, None]:
    with Network() as network:
        yield network


@pytest.fixture(scope="session")
def k3s_in_network(proxy_network: Network) -> Generator[K3SContainer, None, None]:
    container = K3SContainer(enable_cgroup_mount=False)
    host_ip = container.get_container_host_ip()
    # Rebuild command to add k3s docker-network alias in the TLS SANs.
    # with_command replaces the command set by K3SContainer.__init__.
    container.with_command(
        f"server --disable traefik --tls-san={host_ip} --tls-san=k3s"
    )
    container.with_network(proxy_network)
    container.with_network_aliases("k3s")
    with container as k3s:
        yield k3s


@pytest.fixture(scope="session")
def squid(proxy_network: Network) -> Generator[DockerContainer, None, None]:
    container = DockerContainer("ubuntu/squid:edge")
    container.with_network(proxy_network)
    container.with_exposed_ports(3128)
    # Write the config inside the container instead of bind-mounting it from the host.
    # A host bind mount fails on Docker daemons running in a VM (e.g. Colima) when the
    # host path is not shared into the VM — Docker then creates an empty directory at
    # the missing path and tries to mount it onto the file in the image, which fails
    # with "trying to mount a directory onto a file".
    # ubuntu/squid:edge does not ship apache2-utils, so generate the htpasswd-format
    # entry with openssl (already in the image). basic_ncsa_auth understands the
    # $apr1$ Apache MD5 format. -d 1 routes startup messages to stderr so the
    # wait_for_logs() predicate can match "Accepting HTTP Socket connections".
    startup_script = (
        f"cat > /etc/squid/squid.conf <<'{_SQUID_CONF_HEREDOC}'\n"
        f"{_SQUID_CONF}"
        f"{_SQUID_CONF_HEREDOC}\n"
        f'printf "{SQUID_PROXY_USER}:%s\\n" "$(openssl passwd -apr1 -salt kubexpwd {shlex.quote(SQUID_PROXY_PASSWORD)})"'
        " > /etc/squid/passwords\n"
        "exec squid -N -d 1 -f /etc/squid/squid.conf\n"
    )
    # Pass the script as a single-element list so docker-py does not shlex-split it
    # into separate tokens (which would only leave "cat" as the -ec argument).
    container.with_kwargs(entrypoint=["sh", "-ec"])
    container.with_command([startup_script])
    with container:
        wait_for_logs(container, "Accepting HTTP Socket connections")
        yield container


@pytest.fixture(scope="session")
def proxy_url(squid: DockerContainer) -> str:
    host = squid.get_container_host_ip()
    port = squid.get_exposed_port(3128)
    return f"http://{host}:{port}"


@pytest.fixture
async def kubernetes_config_via_proxy(
    k3s_in_network: K3SContainer,
) -> AsyncGenerator[ClientConfiguration, None]:
    conf = safe_load(k3s_in_network.config_yaml())
    config = KubeConfig.model_validate(conf)
    client_config = await configure_from_kubeconfig(config)
    # Route through the in-network alias that squid can resolve and K3S has in SANs;
    # the --tls-san=k3s flag added in k3s_in_network keeps TLS validation working.
    client_config.base_url = "https://k3s:6443"
    yield client_config


@pytest.fixture
def proxy_netrc(tmp_path: Path, proxy_url: str) -> Path:
    host = urlparse(proxy_url).hostname or ""
    netrc_file = tmp_path / "netrc"
    netrc_file.write_text(
        f"machine {host}\nlogin {SQUID_PROXY_USER}\npassword {SQUID_PROXY_PASSWORD}\n"
    )
    netrc_file.chmod(stat.S_IRUSR | stat.S_IWUSR)
    return netrc_file


@pytest.fixture(scope="session")
def sa_token_via_proxy(k3s_in_network: K3SContainer) -> str:
    return mint_sa_token(k3s_in_network)


@pytest.fixture(scope="session")
def sa_admin_token_via_proxy(k3s_in_network: K3SContainer) -> str:
    return mint_sa_token(
        k3s_in_network,
        sa_name="kubex-test-admin-sa",
        crb_name="kubex-test-admin-sa-binding",
        clusterrole="admin",
    )


@pytest.fixture
async def kubernetes_token_config_via_proxy(
    kubernetes_config_via_proxy: ClientConfiguration,
    sa_token_via_proxy: str,
) -> ClientConfiguration:
    kubernetes_config_via_proxy.client_cert_file = None
    kubernetes_config_via_proxy.client_key_file = None
    kubernetes_config_via_proxy._token = sa_token_via_proxy
    return kubernetes_config_via_proxy


@pytest.fixture
async def kubernetes_admin_token_config_via_proxy(
    kubernetes_config_via_proxy: ClientConfiguration,
    sa_admin_token_via_proxy: str,
) -> ClientConfiguration:
    kubernetes_config_via_proxy.client_cert_file = None
    kubernetes_config_via_proxy.client_key_file = None
    kubernetes_config_via_proxy._token = sa_admin_token_via_proxy
    return kubernetes_config_via_proxy


@pytest.fixture
async def tmp_namespace_via_proxy(
    k3s_in_network: K3SContainer,
) -> AsyncGenerator[Namespace, None]:
    conf = safe_load(k3s_in_network.config_yaml())
    config = KubeConfig.model_validate(conf)
    # Build a direct-access config (no base_url override) so namespace provisioning
    # bypasses Squid and hits the host-port mapping directly.
    direct_config = await configure_from_kubeconfig(config)
    namespace_template = Namespace(
        metadata=ObjectMetadata(generate_name="test-ws-proxy-")
    )
    async with HttpxClient(direct_config) as client:
        api: Api[Namespace] = Api(Namespace, client=client)
        namespace = await api.create(namespace_template)
        assert namespace.metadata.name is not None
        yield namespace
        await api.delete(namespace.metadata.name)


@pytest.fixture
def tmp_namespace_name_via_proxy(
    tmp_namespace_via_proxy: Namespace,
) -> Generator[str, None, None]:
    assert tmp_namespace_via_proxy.metadata.name is not None
    yield tmp_namespace_via_proxy.metadata.name


@pytest.fixture(autouse=True)
def clean_proxy_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in (
        "http_proxy",
        "HTTP_PROXY",
        "https_proxy",
        "HTTPS_PROXY",
        "ws_proxy",
        "WS_PROXY",
        "wss_proxy",
        "WSS_PROXY",
        "all_proxy",
        "ALL_PROXY",
        "NO_PROXY",
        "no_proxy",
        "NETRC",
    ):
        monkeypatch.delenv(var, raising=False)
