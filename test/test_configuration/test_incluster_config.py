from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from kubex.core.exceptions import ConfigurationError
from kubex.configuration.incluster_config import (
    DEFAULT_CERT_FILENAME,
    DEFAULT_TOKEN_FILENAME,
    KUBERNETES_SERVICE_HOST_ENV,
    KUBERNETES_SERVICE_PORT_ENV,
    configure_from_pod_env,
)

MODULE = "kubex.configuration.incluster_config"


@pytest.fixture()
def namespace_file(tmp_path: Path) -> Path:
    ns_file = tmp_path / "namespace"
    ns_file.write_text("test-namespace\n")
    return ns_file


@pytest.fixture()
def token_file(tmp_path: Path) -> Path:
    tf = tmp_path / "token"
    tf.write_text("fake-token")
    return tf


@pytest.fixture()
def cert_file(tmp_path: Path) -> Path:
    cf = tmp_path / "ca.crt"
    cf.write_text("fake-ca-cert")
    return cf


@pytest.mark.anyio
async def test_happy_path_with_explicit_params(
    namespace_file: Path, token_file: Path, cert_file: Path
) -> None:
    with patch(f"{MODULE}.DEFAULT_NAMESAPCE_FILENAME", namespace_file):
        config = await configure_from_pod_env(
            token_filename=token_file,
            cert_filename=cert_file,
            kubernetes_service_host="10.0.0.1",
            kubernetes_service_port="443",
        )
    assert config.base_url == "https://10.0.0.1:443"
    assert config.namespace == "test-namespace"
    assert config.token_file == token_file
    assert config.server_ca_file == cert_file
    assert config.client_cert_file is None
    assert config.client_key_file is None


@pytest.mark.anyio
async def test_url_construction(
    namespace_file: Path, token_file: Path, cert_file: Path
) -> None:
    with patch(f"{MODULE}.DEFAULT_NAMESAPCE_FILENAME", namespace_file):
        config = await configure_from_pod_env(
            token_filename=token_file,
            cert_filename=cert_file,
            kubernetes_service_host="api.k8s.local",
            kubernetes_service_port="6443",
        )
    assert config.base_url == "https://api.k8s.local:6443"


@pytest.mark.anyio
async def test_env_var_fallback_for_host_and_port(
    namespace_file: Path, token_file: Path, cert_file: Path
) -> None:
    env = {
        KUBERNETES_SERVICE_HOST_ENV: "192.168.1.100",
        KUBERNETES_SERVICE_PORT_ENV: "8443",
    }
    with (
        patch.dict("os.environ", env, clear=False),
        patch(f"{MODULE}.DEFAULT_NAMESAPCE_FILENAME", namespace_file),
    ):
        config = await configure_from_pod_env(
            token_filename=token_file,
            cert_filename=cert_file,
        )
    assert config.base_url == "https://192.168.1.100:8443"


@pytest.mark.anyio
async def test_env_var_not_used_when_explicit_params_provided(
    namespace_file: Path, token_file: Path, cert_file: Path
) -> None:
    env = {
        KUBERNETES_SERVICE_HOST_ENV: "should-not-use",
        KUBERNETES_SERVICE_PORT_ENV: "9999",
    }
    with (
        patch.dict("os.environ", env, clear=False),
        patch(f"{MODULE}.DEFAULT_NAMESAPCE_FILENAME", namespace_file),
    ):
        config = await configure_from_pod_env(
            token_filename=token_file,
            cert_filename=cert_file,
            kubernetes_service_host="explicit-host",
            kubernetes_service_port="443",
        )
    assert config.base_url == "https://explicit-host:443"


@pytest.mark.anyio
async def test_default_token_filename_when_not_provided(
    namespace_file: Path, cert_file: Path
) -> None:
    with patch(f"{MODULE}.DEFAULT_NAMESAPCE_FILENAME", namespace_file):
        config = await configure_from_pod_env(
            cert_filename=cert_file,
            kubernetes_service_host="10.0.0.1",
            kubernetes_service_port="443",
        )
    assert config.token_file == DEFAULT_TOKEN_FILENAME


@pytest.mark.anyio
async def test_default_cert_filename_when_not_provided(
    namespace_file: Path, token_file: Path
) -> None:
    with patch(f"{MODULE}.DEFAULT_NAMESAPCE_FILENAME", namespace_file):
        config = await configure_from_pod_env(
            token_filename=token_file,
            kubernetes_service_host="10.0.0.1",
            kubernetes_service_port="443",
        )
    assert config.server_ca_file == DEFAULT_CERT_FILENAME


@pytest.mark.anyio
async def test_namespace_read_from_file_and_stripped(
    tmp_path: Path, token_file: Path, cert_file: Path
) -> None:
    ns_file = tmp_path / "namespace"
    ns_file.write_text("  spaced-namespace  \n")
    with patch(f"{MODULE}.DEFAULT_NAMESAPCE_FILENAME", ns_file):
        config = await configure_from_pod_env(
            token_filename=token_file,
            cert_filename=cert_file,
            kubernetes_service_host="10.0.0.1",
            kubernetes_service_port="443",
        )
    assert config.namespace == "spaced-namespace"


@pytest.mark.anyio
async def test_try_refresh_token_defaults_to_true(
    namespace_file: Path, token_file: Path, cert_file: Path
) -> None:
    with patch(f"{MODULE}.DEFAULT_NAMESAPCE_FILENAME", namespace_file):
        config = await configure_from_pod_env(
            token_filename=token_file,
            cert_filename=cert_file,
            kubernetes_service_host="10.0.0.1",
            kubernetes_service_port="443",
        )
    assert config.try_refresh_token is True


@pytest.mark.anyio
async def test_try_refresh_token_can_be_set_to_false(
    namespace_file: Path, token_file: Path, cert_file: Path
) -> None:
    with patch(f"{MODULE}.DEFAULT_NAMESAPCE_FILENAME", namespace_file):
        config = await configure_from_pod_env(
            token_filename=token_file,
            cert_filename=cert_file,
            kubernetes_service_host="10.0.0.1",
            kubernetes_service_port="443",
            try_refresh_token=False,
        )
    assert config.try_refresh_token is False


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("host", "expected"),
    [
        ("fd00:10:96::1", "https://[fd00:10:96::1]:443"),
        ("[fd00:10:96::1]", "https://[fd00:10:96::1]:443"),
        ("10.96.0.1", "https://10.96.0.1:443"),
    ],
)
async def test_ipv6_service_host_is_bracketed(
    host: str, expected: str, namespace_file: Path, token_file: Path, cert_file: Path
) -> None:
    with patch(f"{MODULE}.DEFAULT_NAMESAPCE_FILENAME", namespace_file):
        config = await configure_from_pod_env(
            token_filename=token_file,
            cert_filename=cert_file,
            kubernetes_service_host=host,
            kubernetes_service_port="443",
        )
    assert config.base_url == expected


@pytest.mark.anyio
@pytest.mark.parametrize(
    "env",
    [
        {},
        {KUBERNETES_SERVICE_HOST_ENV: "10.0.0.1"},
        {KUBERNETES_SERVICE_PORT_ENV: "443"},
        {KUBERNETES_SERVICE_HOST_ENV: "", KUBERNETES_SERVICE_PORT_ENV: "443"},
    ],
)
async def test_missing_service_env_raises_configuration_error(
    env: dict[str, str], token_file: Path, cert_file: Path
) -> None:
    with patch.dict("os.environ", env, clear=True):
        with pytest.raises(ConfigurationError, match="not running inside a"):
            await configure_from_pod_env(
                token_filename=token_file, cert_filename=cert_file
            )


@pytest.mark.anyio
@pytest.mark.parametrize("contents", [None, "", "  \n"])
async def test_namespace_falls_back_to_default(
    contents: str | None, tmp_path: Path, token_file: Path, cert_file: Path
) -> None:
    ns_file = tmp_path / "namespace"
    if contents is not None:
        ns_file.write_text(contents)
    with patch(f"{MODULE}.DEFAULT_NAMESAPCE_FILENAME", ns_file):
        config = await configure_from_pod_env(
            token_filename=token_file,
            cert_filename=cert_file,
            kubernetes_service_host="10.0.0.1",
            kubernetes_service_port="443",
        )
    assert config.namespace == "default"
