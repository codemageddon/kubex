from __future__ import annotations

from collections.abc import Generator
from typing import Any

import atexit
from base64 import b64encode
from pathlib import Path
from unittest.mock import patch

import pytest
from yaml import dump

from kubex.configuration.configuration import KubeConfig
from kubex.configuration.file_config import (
    DEFAULT_KUBE_CONFIG_FILE,
    KUBECONFIG_ENV_VARIABLE,
    _cleanup_temp_files,
    _decode_and_put_to_file,
    _get_kube_config_file,
    _load_kube_config,
    _temp_files,
    configure_from_kubeconfig,
)


@pytest.fixture()
def clean_temp_files() -> Generator[dict[str, Path], None, None]:
    """Save, clear, and restore the module-level _temp_files dict."""
    original = _temp_files.copy()
    _temp_files.clear()
    yield _temp_files
    for p in _temp_files.values():
        if p.exists():
            p.unlink(missing_ok=True)
    _temp_files.clear()
    _temp_files.update(original)


def _minimal_kubeconfig(
    *,
    cluster_name: str = "test-cluster",
    server: str = "https://localhost:6443",
    user_name: str = "test-user",
    context_name: str = "test-context",
    current_context: str | None = "test-context",
    ca_data: str | None = None,
    ca_file: str | None = None,
    client_cert_data: str | None = None,
    client_cert_file: str | None = None,
    client_key_data: str | None = None,
    client_key_file: str | None = None,
) -> dict[str, Any]:
    cluster: dict[str, Any] = {"server": server}
    if ca_data is not None:
        cluster["certificate-authority-data"] = ca_data
    if ca_file is not None:
        cluster["certificate-authority"] = ca_file
    user: dict[str, Any] = {}
    if client_cert_data is not None:
        user["client-certificate-data"] = client_cert_data
    if client_cert_file is not None:
        user["client-certificate"] = client_cert_file
    if client_key_data is not None:
        user["client-key-data"] = client_key_data
    if client_key_file is not None:
        user["client-key"] = client_key_file
    result: dict[str, Any] = {
        "apiVersion": "v1",
        "kind": "Config",
        "clusters": [{"name": cluster_name, "cluster": cluster}],
        "users": [{"name": user_name, "user": user}],
        "contexts": [
            {
                "name": context_name,
                "context": {"cluster": cluster_name, "user": user_name},
            }
        ],
    }
    if current_context is not None:
        result["current-context"] = current_context
    return result


def _write_kubeconfig(path: Path, data: dict[str, Any]) -> Path:
    path.write_text(dump(data))
    return path


def test_get_kube_config_file_default() -> None:
    with patch.dict("os.environ", {}, clear=True):
        result = _get_kube_config_file()
    assert result == DEFAULT_KUBE_CONFIG_FILE


def test_get_kube_config_file_env_var(tmp_path: Path) -> None:
    custom_path = tmp_path / "custom-config"
    custom_path.touch()
    with patch.dict("os.environ", {KUBECONFIG_ENV_VARIABLE: str(custom_path)}):
        result = _get_kube_config_file()
    assert result == custom_path.resolve()


def test_get_kube_config_file_env_var_resolves_relative() -> None:
    with patch.dict("os.environ", {KUBECONFIG_ENV_VARIABLE: "./relative/config"}):
        result = _get_kube_config_file()
    assert result.is_absolute()
    assert result == Path("./relative/config").resolve()


def test_load_kube_config_from_path(tmp_path: Path) -> None:
    data = _minimal_kubeconfig()
    config_file = _write_kubeconfig(tmp_path / "config", data)
    config = _load_kube_config(config_file)
    assert isinstance(config, KubeConfig)
    assert config.current_context == "test-context"
    assert len(config.clusters) == 1
    assert config.clusters[0].name == "test-cluster"
    assert len(config.users) == 1
    assert config.users[0].name == "test-user"
    assert len(config.contexts) == 1
    assert config.contexts[0].name == "test-context"


def test_load_kube_config_uses_default_when_no_path(tmp_path: Path) -> None:
    data = _minimal_kubeconfig()
    config_file = tmp_path / "config"
    _write_kubeconfig(config_file, data)
    with patch(
        "kubex.configuration.file_config._get_kube_config_file",
        return_value=config_file,
    ):
        config = _load_kube_config()
    assert config.current_context == "test-context"


def test_load_kube_config_custom_path(tmp_path: Path) -> None:
    data = _minimal_kubeconfig(
        server="https://custom:8443",
        current_context="custom-ctx",
        context_name="custom-ctx",
    )
    config_file = _write_kubeconfig(tmp_path / "custom", data)
    config = _load_kube_config(config_file)
    assert config.current_context == "custom-ctx"
    assert str(config.clusters[0].cluster.server) == "https://custom:8443/"


@pytest.mark.anyio
async def test_configure_from_kubeconfig_happy_path(tmp_path: Path) -> None:
    data = _minimal_kubeconfig()
    config_file = _write_kubeconfig(tmp_path / "config", data)
    kube_config = _load_kube_config(config_file)
    client_config = await configure_from_kubeconfig(config=kube_config)
    assert client_config.base_url == "https://localhost:6443/"


@pytest.mark.anyio
async def test_configure_from_kubeconfig_explicit_use_context(tmp_path: Path) -> None:
    data = _minimal_kubeconfig()
    extra_context = {
        "name": "other-context",
        "context": {"cluster": "test-cluster", "user": "test-user"},
    }
    data["contexts"].append(extra_context)
    config_file = _write_kubeconfig(tmp_path / "config", data)
    kube_config = _load_kube_config(config_file)
    client_config = await configure_from_kubeconfig(
        config=kube_config, use_context="other-context"
    )
    assert client_config.base_url == "https://localhost:6443/"


@pytest.mark.anyio
async def test_configure_from_kubeconfig_no_current_context() -> None:
    kube_config = KubeConfig(clusters=[], users=[], contexts=[], current_context=None)
    with pytest.raises(ValueError, match="No current context"):
        await configure_from_kubeconfig(config=kube_config)


@pytest.mark.anyio
async def test_configure_from_kubeconfig_context_not_found() -> None:
    kube_config = KubeConfig(
        clusters=[], users=[], contexts=[], current_context="missing"
    )
    with pytest.raises(ValueError, match="Context missing not found"):
        await configure_from_kubeconfig(config=kube_config)


@pytest.mark.anyio
async def test_configure_from_kubeconfig_cluster_not_found(tmp_path: Path) -> None:
    data = _minimal_kubeconfig()
    data["clusters"] = []
    config_file = _write_kubeconfig(tmp_path / "config", data)
    kube_config = _load_kube_config(config_file)
    with pytest.raises(ValueError, match="Cluster test-cluster not found"):
        await configure_from_kubeconfig(config=kube_config)


@pytest.mark.anyio
async def test_configure_from_kubeconfig_user_not_found(tmp_path: Path) -> None:
    data = _minimal_kubeconfig()
    data["users"] = []
    config_file = _write_kubeconfig(tmp_path / "config", data)
    kube_config = _load_kube_config(config_file)
    with pytest.raises(ValueError, match="User test-user not found"):
        await configure_from_kubeconfig(config=kube_config)


@pytest.mark.anyio
async def test_configure_from_kubeconfig_loads_config_when_none_provided(
    tmp_path: Path,
) -> None:
    data = _minimal_kubeconfig()
    config_file = _write_kubeconfig(tmp_path / "config", data)
    with patch(
        "kubex.configuration.file_config._load_kube_config",
        return_value=_load_kube_config(config_file),
    ):
        client_config = await configure_from_kubeconfig()
    assert client_config.base_url == "https://localhost:6443/"


def test_decode_and_put_to_file_basic(clean_temp_files: dict[str, Path]) -> None:
    payload = b"test-certificate-data"
    encoded = b64encode(payload).decode()
    result = _decode_and_put_to_file(encoded)
    assert result.exists()
    assert result.read_bytes() == payload


def test_decode_and_put_to_file_caching(clean_temp_files: dict[str, Path]) -> None:
    payload = b"cached-cert"
    encoded = b64encode(payload).decode()
    first = _decode_and_put_to_file(encoded)
    second = _decode_and_put_to_file(encoded)
    assert first == second


def test_decode_and_put_to_file_different_data_different_files(
    clean_temp_files: dict[str, Path],
) -> None:
    data1 = b64encode(b"cert-one").decode()
    data2 = b64encode(b"cert-two").decode()
    path1 = _decode_and_put_to_file(data1)
    path2 = _decode_and_put_to_file(data2)
    assert path1 != path2
    assert path1.read_bytes() == b"cert-one"
    assert path2.read_bytes() == b"cert-two"


def test_decode_and_put_to_file_registers_atexit(
    clean_temp_files: dict[str, Path],
) -> None:
    encoded = b64encode(b"atexit-test").decode()
    with patch.object(atexit, "register") as mock_register:
        _decode_and_put_to_file(encoded)
        mock_register.assert_called_once_with(_cleanup_temp_files)


def test_decode_and_put_to_file_atexit_not_reregistered(
    clean_temp_files: dict[str, Path],
) -> None:
    _temp_files["existing-key"] = Path("/dummy")
    encoded = b64encode(b"no-reregister").decode()
    with patch.object(atexit, "register") as mock_register:
        _decode_and_put_to_file(encoded)
        mock_register.assert_not_called()


def test_cleanup_temp_files(clean_temp_files: dict[str, Path]) -> None:
    path1 = _decode_and_put_to_file(b64encode(b"cleanup1").decode())
    path2 = _decode_and_put_to_file(b64encode(b"cleanup2").decode())
    assert path1.exists()
    assert path2.exists()
    _cleanup_temp_files()
    assert not path1.exists()
    assert not path2.exists()


@pytest.mark.anyio
async def test_configure_cert_authority_data(
    tmp_path: Path, clean_temp_files: dict[str, Path]
) -> None:
    ca_cert = b"-----BEGIN CERTIFICATE-----\nfake-ca-cert\n-----END CERTIFICATE-----"
    ca_data = b64encode(ca_cert).decode()
    data = _minimal_kubeconfig(ca_data=ca_data)
    config_file = _write_kubeconfig(tmp_path / "config", data)
    kube_config = _load_kube_config(config_file)

    client_config = await configure_from_kubeconfig(config=kube_config)
    assert client_config.server_ca_file is not None
    assert client_config.server_ca_file.read_bytes() == ca_cert


@pytest.mark.anyio
async def test_configure_client_cert_and_key_data(
    tmp_path: Path, clean_temp_files: dict[str, Path]
) -> None:
    cert = b"-----BEGIN CERTIFICATE-----\nfake-client-cert\n-----END CERTIFICATE-----"
    key = b"-----BEGIN RSA PRIVATE KEY-----\nfake-key\n-----END RSA PRIVATE KEY-----"
    cert_data = b64encode(cert).decode()
    key_data = b64encode(key).decode()
    data = _minimal_kubeconfig(client_cert_data=cert_data, client_key_data=key_data)
    config_file = _write_kubeconfig(tmp_path / "config", data)
    kube_config = _load_kube_config(config_file)

    client_config = await configure_from_kubeconfig(config=kube_config)
    assert client_config.client_cert_file is not None
    assert client_config.client_cert_file.read_bytes() == cert
    assert client_config.client_key_file is not None
    assert client_config.client_key_file.read_bytes() == key


@pytest.mark.anyio
async def test_configure_cert_authority_file_takes_precedence(
    tmp_path: Path,
) -> None:
    ca_file = tmp_path / "ca.crt"
    ca_file.write_text("real-ca-from-file")
    ca_data = b64encode(b"should-not-use-this").decode()
    data = _minimal_kubeconfig(ca_file=str(ca_file), ca_data=ca_data)
    config_file = _write_kubeconfig(tmp_path / "config", data)
    kube_config = _load_kube_config(config_file)
    client_config = await configure_from_kubeconfig(config=kube_config)
    assert client_config.server_ca_file == ca_file


@pytest.mark.anyio
async def test_configure_client_cert_file_takes_precedence(tmp_path: Path) -> None:
    cert_file = tmp_path / "client.crt"
    cert_file.write_text("real-cert-from-file")
    key_file = tmp_path / "client.key"
    key_file.write_text("real-key-from-file")
    cert_data = b64encode(b"should-not-use-cert").decode()
    key_data = b64encode(b"should-not-use-key").decode()
    data = _minimal_kubeconfig(
        client_cert_file=str(cert_file),
        client_key_file=str(key_file),
        client_cert_data=cert_data,
        client_key_data=key_data,
    )
    config_file = _write_kubeconfig(tmp_path / "config", data)
    kube_config = _load_kube_config(config_file)
    client_config = await configure_from_kubeconfig(config=kube_config)
    assert client_config.client_cert_file == cert_file
    assert client_config.client_key_file == key_file


@pytest.mark.anyio
async def test_configure_no_certs() -> None:
    data = _minimal_kubeconfig()
    kube_config = KubeConfig.model_validate(data)
    client_config = await configure_from_kubeconfig(config=kube_config)
    assert client_config.server_ca_file is None
    assert client_config.client_cert_file is None
    assert client_config.client_key_file is None
