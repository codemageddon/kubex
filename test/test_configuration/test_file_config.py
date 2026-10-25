from __future__ import annotations

from collections.abc import Generator
from typing import Any

import atexit
import json
import os
import sys
import time
import warnings
from base64 import b64encode, urlsafe_b64encode
from pathlib import Path
from unittest.mock import patch

import pytest
from yaml import dump

from kubex.configuration.auth.refreshable_token import (
    ExecRefreshableToken,
    OidcRefreshableToken,
)
from kubex.configuration import file_config
from kubex.configuration.auth.exec import ExecCredentialCluster
from kubex.configuration.configuration import KubeConfig
from kubex.core.exceptions import ConfigurationError, ConfigurationValueError

from kubex.configuration.file_config import (
    DEFAULT_KUBE_CONFIG_FILE,
    KUBECONFIG_ENV_VARIABLE,
    _cleanup_temp_files,
    _decode_and_put_to_file,
    _get_kube_config_file,
    _get_kube_config_files,
    _load_kube_config,
    _temp_files,
    _TempFile,
    configure_from_kubeconfig,
)


@pytest.fixture()
def clean_temp_files(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[dict[str, _TempFile], None, None]:
    """Save, clear, and restore the module-level temp-file bookkeeping."""
    original = _temp_files.copy()
    _temp_files.clear()
    monkeypatch.setattr(file_config, "_cleanup_registered", False)
    yield _temp_files
    for temp_file in _temp_files.values():
        temp_file.path.unlink(missing_ok=True)
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
    token: str | None = None,
    token_file: str | None = None,
    insecure_skip_tls_verify: bool | None = None,
    proxy_url: str | None = None,
) -> dict[str, Any]:
    cluster: dict[str, Any] = {"server": server}
    if ca_data is not None:
        cluster["certificate-authority-data"] = ca_data
    if ca_file is not None:
        cluster["certificate-authority"] = ca_file
    if insecure_skip_tls_verify is not None:
        cluster["insecure-skip-tls-verify"] = insecure_skip_tls_verify
    if proxy_url is not None:
        cluster["proxy-url"] = proxy_url
    user: dict[str, Any] = {}
    if client_cert_data is not None:
        user["client-certificate-data"] = client_cert_data
    if client_cert_file is not None:
        user["client-certificate"] = client_cert_file
    if client_key_data is not None:
        user["client-key-data"] = client_key_data
    if client_key_file is not None:
        user["client-key"] = client_key_file
    if token is not None:
        user["token"] = token
    if token_file is not None:
        user["tokenFile"] = token_file
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


def test_get_kube_config_files_no_env_var_returns_default() -> None:
    with patch.dict("os.environ", {}, clear=True):
        result = _get_kube_config_files()
    assert result == [DEFAULT_KUBE_CONFIG_FILE]


def test_get_kube_config_files_splits_pathsep_list(tmp_path: Path) -> None:
    first = tmp_path / "first-config"
    second = tmp_path / "second-config"
    value = os.pathsep.join([str(first), str(second)])
    with patch.dict("os.environ", {KUBECONFIG_ENV_VARIABLE: value}):
        result = _get_kube_config_files()
    assert result == [first.resolve(), second.resolve()]


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
        "kubex.configuration.file_config._get_kube_config_files",
        return_value=[config_file],
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
    assert config.clusters[0].cluster.server == "https://custom:8443"


def test_load_kube_config_resolves_relative_certificate_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kube_dir = tmp_path / "kube-dir"
    kube_dir.mkdir()
    (kube_dir / "ca.crt").write_text("kubeconfig-dir-ca")
    data = _minimal_kubeconfig(ca_file="ca.crt")
    config_file = _write_kubeconfig(kube_dir / "config", data)

    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    # A same-named file in cwd must not be picked instead of the real one.
    (elsewhere / "ca.crt").write_text("wrong-file-from-cwd")
    monkeypatch.chdir(elsewhere)

    config = _load_kube_config(config_file)
    assert config.clusters[0].cluster.certificate_authority is not None
    assert (
        config.clusters[0].cluster.certificate_authority.read_text()
        == "kubeconfig-dir-ca"
    )


def test_load_kube_config_resolves_relative_user_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kube_dir = tmp_path / "kube-dir"
    kube_dir.mkdir()
    (kube_dir / "client.crt").write_text("client-cert")
    (kube_dir / "client.key").write_text("client-key")
    (kube_dir / "token").write_text("token-from-file")
    data = _minimal_kubeconfig(
        client_cert_file="client.crt",
        client_key_file="client.key",
        token_file="token",
    )
    config_file = _write_kubeconfig(kube_dir / "config", data)

    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    config = _load_kube_config(config_file)
    user = config.users[0].auth_info
    assert user.client_certificate is not None
    assert user.client_certificate.read_text() == "client-cert"
    assert user.client_key is not None
    assert user.client_key.read_text() == "client-key"
    assert user.token_file is not None
    assert user.token_file.read_text() == "token-from-file"


def test_load_kube_config_leaves_absolute_paths_untouched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ca_file = tmp_path / "absolute-ca.crt"
    ca_file.write_text("absolute-ca")
    kube_dir = tmp_path / "kube-dir"
    kube_dir.mkdir()
    data = _minimal_kubeconfig(ca_file=str(ca_file))
    config_file = _write_kubeconfig(kube_dir / "config", data)

    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    config = _load_kube_config(config_file)
    assert config.clusters[0].cluster.certificate_authority == ca_file.resolve()


def test_load_kube_config_merges_multiple_kubeconfig_files(tmp_path: Path) -> None:
    first = _write_kubeconfig(
        tmp_path / "first",
        _minimal_kubeconfig(
            cluster_name="cluster-a",
            server="https://a:6443",
            user_name="user-a",
            context_name="ctx-a",
            current_context="ctx-a",
        ),
    )
    second = _write_kubeconfig(
        tmp_path / "second",
        _minimal_kubeconfig(
            cluster_name="cluster-b",
            server="https://b:6443",
            user_name="user-b",
            context_name="ctx-b",
            current_context="ctx-b",
        ),
    )
    value = os.pathsep.join([str(first), str(second)])
    with patch.dict("os.environ", {KUBECONFIG_ENV_VARIABLE: value}):
        config = _load_kube_config()

    assert {c.name for c in config.clusters} == {"cluster-a", "cluster-b"}
    assert {u.name for u in config.users} == {"user-a", "user-b"}
    assert {c.name for c in config.contexts} == {"ctx-a", "ctx-b"}
    # current-context is taken from the first file that sets it.
    assert config.current_context == "ctx-a"


def test_load_kube_config_merge_skips_empty_current_context(tmp_path: Path) -> None:
    first_data = _minimal_kubeconfig(
        cluster_name="cluster-a",
        server="https://a:6443",
        user_name="user-a",
        context_name="ctx-a",
        current_context=None,
    )
    # A client-go-written kubeconfig with no selected context has a literal
    # `current-context: ""`, not an absent key.
    first_data["current-context"] = ""
    first = _write_kubeconfig(tmp_path / "first", first_data)
    second = _write_kubeconfig(
        tmp_path / "second",
        _minimal_kubeconfig(
            cluster_name="cluster-b",
            server="https://b:6443",
            user_name="user-b",
            context_name="ctx-b",
            current_context="ctx-b",
        ),
    )
    value = os.pathsep.join([str(first), str(second)])
    with patch.dict("os.environ", {KUBECONFIG_ENV_VARIABLE: value}):
        config = _load_kube_config()

    # An empty scalar in the first file does not count as "set"; the second
    # file's value is used instead.
    assert config.current_context == "ctx-b"


def test_load_kube_config_multi_file_first_file_wins_on_name_conflict(
    tmp_path: Path,
) -> None:
    first = _write_kubeconfig(
        tmp_path / "first",
        _minimal_kubeconfig(server="https://first:6443"),
    )
    second = _write_kubeconfig(
        tmp_path / "second",
        _minimal_kubeconfig(server="https://second:6443"),
    )
    value = os.pathsep.join([str(first), str(second)])
    with patch.dict("os.environ", {KUBECONFIG_ENV_VARIABLE: value}):
        config = _load_kube_config()

    assert len(config.clusters) == 1
    assert config.clusters[0].cluster.server == "https://first:6443"


def test_load_kube_config_multi_file_skips_missing_files(tmp_path: Path) -> None:
    real = _write_kubeconfig(tmp_path / "real", _minimal_kubeconfig())
    missing = tmp_path / "does-not-exist"
    value = os.pathsep.join([str(missing), str(real)])
    with patch.dict("os.environ", {KUBECONFIG_ENV_VARIABLE: value}):
        config = _load_kube_config()

    assert config.current_context == "test-context"


def test_load_kube_config_multi_file_all_missing_raises_file_not_found(
    tmp_path: Path,
) -> None:
    value = os.pathsep.join([str(tmp_path / "a"), str(tmp_path / "b")])
    with patch.dict("os.environ", {KUBECONFIG_ENV_VARIABLE: value}):
        with pytest.raises(FileNotFoundError):
            _load_kube_config()


def test_load_kube_config_multi_file_skips_empty_file(tmp_path: Path) -> None:
    empty = tmp_path / "empty.yaml"
    empty.touch()
    real = _write_kubeconfig(tmp_path / "real", _minimal_kubeconfig())
    value = os.pathsep.join([str(real), str(empty)])
    with patch.dict("os.environ", {KUBECONFIG_ENV_VARIABLE: value}):
        config = _load_kube_config()

    assert config.current_context == "test-context"


def test_load_kube_config_all_files_empty_raises_file_not_found(
    tmp_path: Path,
) -> None:
    first = tmp_path / "first.yaml"
    first.touch()
    second = tmp_path / "second.yaml"
    second.touch()
    value = os.pathsep.join([str(first), str(second)])
    with patch.dict("os.environ", {KUBECONFIG_ENV_VARIABLE: value}):
        with pytest.raises(FileNotFoundError):
            _load_kube_config()


def test_load_kube_config_non_mapping_document_raises_configuration_error(
    tmp_path: Path,
) -> None:
    # A bare YAML list is not an empty document (unlike a `None` parse from an
    # empty file) and must not be silently dropped and treated as "missing".
    bad = tmp_path / "not-a-mapping.yaml"
    bad.write_text("- just\n- a\n- list\n")
    with patch.dict("os.environ", {KUBECONFIG_ENV_VARIABLE: str(bad)}):
        with pytest.raises(ConfigurationError, match="expected a kubeconfig mapping"):
            _load_kube_config()


@pytest.mark.anyio
async def test_configure_from_kubeconfig_happy_path(tmp_path: Path) -> None:
    data = _minimal_kubeconfig()
    config_file = _write_kubeconfig(tmp_path / "config", data)
    kube_config = _load_kube_config(config_file)
    client_config = await configure_from_kubeconfig(config=kube_config)
    assert client_config.base_url == "https://localhost:6443"


@pytest.mark.anyio
async def test_configure_from_kubeconfig_forwards_context_namespace(
    tmp_path: Path,
) -> None:
    data = _minimal_kubeconfig()
    data["contexts"][0]["context"]["namespace"] = "staging"
    config_file = _write_kubeconfig(tmp_path / "config", data)
    kube_config = _load_kube_config(config_file)
    client_config = await configure_from_kubeconfig(config=kube_config)
    assert client_config.namespace == "staging"


@pytest.mark.anyio
async def test_configure_from_kubeconfig_no_context_namespace_defaults_to_default(
    tmp_path: Path,
) -> None:
    # kubectl/client-go use "default"; None would make Api.list()/watch()
    # silently span all namespaces.
    data = _minimal_kubeconfig()
    config_file = _write_kubeconfig(tmp_path / "config", data)
    kube_config = _load_kube_config(config_file)
    client_config = await configure_from_kubeconfig(config=kube_config)
    assert client_config.namespace == "default"


@pytest.mark.anyio
async def test_configure_from_kubeconfig_empty_context_namespace_defaults_to_default() -> (
    None
):
    data = _minimal_kubeconfig()
    data["contexts"][0]["context"]["namespace"] = ""
    client_config = await configure_from_kubeconfig(KubeConfig.model_validate(data))
    assert client_config.namespace == "default"


@pytest.mark.anyio
async def test_configure_from_kubeconfig_invalid_oidc_config_does_not_leak_secret(
    tmp_path: Path,
) -> None:
    data = _minimal_kubeconfig()
    data["users"][0]["user"]["auth-provider"] = {
        "name": "oidc",
        "config": {
            "client-secret": "SUPERSECRET",
            "refresh-token": "REFRESHSECRET",
            # missing required client-id/idp-issuer-url triggers ValidationError
        },
    }
    config_file = _write_kubeconfig(tmp_path / "config", data)
    kube_config = _load_kube_config(config_file)
    with pytest.raises(ConfigurationError) as exc_info:
        await configure_from_kubeconfig(config=kube_config)
    message = str(exc_info.value)
    assert "SUPERSECRET" not in message
    assert "REFRESHSECRET" not in message
    assert exc_info.value.__cause__ is None


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
    assert client_config.base_url == "https://localhost:6443"


@pytest.mark.anyio
async def test_configure_from_kubeconfig_no_current_context() -> None:
    kube_config = KubeConfig(clusters=[], users=[], contexts=[], current_context=None)
    with pytest.raises(ConfigurationValueError, match="No current context"):
        await configure_from_kubeconfig(config=kube_config)


@pytest.mark.anyio
async def test_configure_from_kubeconfig_context_not_found() -> None:
    kube_config = KubeConfig(
        clusters=[], users=[], contexts=[], current_context="missing"
    )
    with pytest.raises(ConfigurationValueError, match="Context missing not found"):
        await configure_from_kubeconfig(config=kube_config)


@pytest.mark.anyio
async def test_configure_from_kubeconfig_cluster_not_found(tmp_path: Path) -> None:
    data = _minimal_kubeconfig()
    data["clusters"] = []
    config_file = _write_kubeconfig(tmp_path / "config", data)
    kube_config = _load_kube_config(config_file)
    with pytest.raises(ConfigurationValueError, match="Cluster test-cluster not found"):
        await configure_from_kubeconfig(config=kube_config)


@pytest.mark.anyio
async def test_configure_from_kubeconfig_user_not_found(tmp_path: Path) -> None:
    data = _minimal_kubeconfig()
    data["users"] = []
    config_file = _write_kubeconfig(tmp_path / "config", data)
    kube_config = _load_kube_config(config_file)
    with pytest.raises(ConfigurationValueError, match="User test-user not found"):
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
    assert client_config.base_url == "https://localhost:6443"


def test_decode_and_put_to_file_basic(clean_temp_files: dict[str, _TempFile]) -> None:
    payload = b"test-certificate-data"
    encoded = b64encode(payload).decode()
    result = _decode_and_put_to_file(encoded)
    assert result.exists()
    assert result.read_bytes() == payload


def test_decode_and_put_to_file_caching(
    clean_temp_files: dict[str, _TempFile],
) -> None:
    payload = b"cached-cert"
    encoded = b64encode(payload).decode()
    first = _decode_and_put_to_file(encoded)
    second = _decode_and_put_to_file(encoded)
    assert first == second


def test_decode_and_put_to_file_different_data_different_files(
    clean_temp_files: dict[str, _TempFile],
) -> None:
    data1 = b64encode(b"cert-one").decode()
    data2 = b64encode(b"cert-two").decode()
    path1 = _decode_and_put_to_file(data1)
    path2 = _decode_and_put_to_file(data2)
    assert path1 != path2
    assert path1.read_bytes() == b"cert-one"
    assert path2.read_bytes() == b"cert-two"


def test_decode_and_put_to_file_registers_atexit(
    clean_temp_files: dict[str, _TempFile],
) -> None:
    with patch.object(atexit, "register") as mock_register:
        _decode_and_put_to_file(b64encode(b"atexit-test").decode())
        _decode_and_put_to_file(b64encode(b"atexit-test-2").decode())
        mock_register.assert_called_once_with(_cleanup_temp_files)


def test_decode_and_put_to_file_atexit_not_reregistered(
    clean_temp_files: dict[str, _TempFile], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(file_config, "_cleanup_registered", True)
    encoded = b64encode(b"no-reregister").decode()
    with patch.object(atexit, "register") as mock_register:
        _decode_and_put_to_file(encoded)
        mock_register.assert_not_called()


def test_decode_and_put_to_file_recreates_deleted_file(
    clean_temp_files: dict[str, _TempFile],
) -> None:
    encoded = b64encode(b"recreate-me").decode()
    first = _decode_and_put_to_file(encoded)
    first.unlink()  # e.g. a tmp cleaner ran
    second = _decode_and_put_to_file(encoded)
    assert second.exists()
    assert second.read_bytes() == b"recreate-me"


def test_cleanup_temp_files_skips_files_created_by_another_process(
    clean_temp_files: dict[str, _TempFile], tmp_path: Path
) -> None:
    # A forked worker inherits the parent's bookkeeping; its exit must not
    # delete files the parent is still using.
    inherited = tmp_path / "inherited"
    inherited.write_bytes(b"parent's")
    _temp_files["inherited"] = _TempFile(inherited, os.getpid() + 1)
    own = _decode_and_put_to_file(b64encode(b"own").decode())
    _cleanup_temp_files()
    assert inherited.exists()
    assert not own.exists()


def test_cleanup_temp_files(clean_temp_files: dict[str, _TempFile]) -> None:
    path1 = _decode_and_put_to_file(b64encode(b"cleanup1").decode())
    path2 = _decode_and_put_to_file(b64encode(b"cleanup2").decode())
    assert path1.exists()
    assert path2.exists()
    _cleanup_temp_files()
    assert not path1.exists()
    assert not path2.exists()


@pytest.mark.anyio
async def test_configure_cert_authority_data(
    tmp_path: Path, clean_temp_files: dict[str, _TempFile]
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
    tmp_path: Path, clean_temp_files: dict[str, _TempFile]
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
async def test_configure_cert_authority_data_takes_precedence(
    tmp_path: Path, clean_temp_files: dict[str, _TempFile]
) -> None:
    # `certificate-authority-data` overrides `certificate-authority`
    # (client-go), even when the file does not exist.
    ca_data = b64encode(b"ca-from-data").decode()
    data = _minimal_kubeconfig(ca_file=str(tmp_path / "missing.crt"), ca_data=ca_data)
    config_file = _write_kubeconfig(tmp_path / "config", data)
    kube_config = _load_kube_config(config_file)
    client_config = await configure_from_kubeconfig(config=kube_config)
    assert client_config.server_ca_file is not None
    assert client_config.server_ca_file.read_bytes() == b"ca-from-data"


@pytest.mark.anyio
async def test_configure_client_cert_data_takes_precedence(
    tmp_path: Path, clean_temp_files: dict[str, _TempFile]
) -> None:
    cert_file = tmp_path / "client.crt"
    cert_file.write_text("cert-from-file")
    key_file = tmp_path / "client.key"
    key_file.write_text("key-from-file")
    data = _minimal_kubeconfig(
        client_cert_file=str(cert_file),
        client_key_file=str(key_file),
        client_cert_data=b64encode(b"cert-from-data").decode(),
        client_key_data=b64encode(b"key-from-data").decode(),
    )
    config_file = _write_kubeconfig(tmp_path / "config", data)
    kube_config = _load_kube_config(config_file)
    client_config = await configure_from_kubeconfig(config=kube_config)
    assert client_config.client_cert_file is not None
    assert client_config.client_cert_file.read_bytes() == b"cert-from-data"
    assert client_config.client_key_file is not None
    assert client_config.client_key_file.read_bytes() == b"key-from-data"


@pytest.mark.anyio
async def test_configure_no_certs() -> None:
    data = _minimal_kubeconfig()
    kube_config = KubeConfig.model_validate(data)
    client_config = await configure_from_kubeconfig(config=kube_config)
    assert client_config.server_ca_file is None
    assert client_config.client_cert_file is None
    assert client_config.client_key_file is None


@pytest.mark.anyio
async def test_configure_insecure_skip_tls_verify_true_forwarded() -> None:
    data = _minimal_kubeconfig(insecure_skip_tls_verify=True)
    kube_config = KubeConfig.model_validate(data)
    client_config = await configure_from_kubeconfig(config=kube_config)
    assert client_config.insecure_skip_tls_verify is True
    assert client_config.verify is False


@pytest.mark.anyio
async def test_configure_insecure_skip_tls_verify_absent_does_not_raise() -> None:
    """Cluster.insecure_skip_tls_verify defaults to False, not None -- forwarding
    it unconditionally would trip ClientConfiguration's "CA required" guard for
    the common system-trust-store kubeconfig (no CA, no insecure flag).
    """
    data = _minimal_kubeconfig()
    kube_config = KubeConfig.model_validate(data)
    client_config = await configure_from_kubeconfig(config=kube_config)
    assert client_config.insecure_skip_tls_verify is None
    assert client_config.verify is None


@pytest.mark.anyio
async def test_configure_proxy_url_warns_and_is_not_applied() -> None:
    data = _minimal_kubeconfig(proxy_url="http://proxy.example:8080")
    kube_config = KubeConfig.model_validate(data)
    with pytest.warns(UserWarning, match="proxy-url"):
        client_config = await configure_from_kubeconfig(config=kube_config)
    # Not applied anywhere on ClientConfiguration -- it belongs on ClientOptions,
    # which this function has no access to.
    assert not hasattr(client_config, "proxy_url")


@pytest.mark.anyio
async def test_configure_no_proxy_url_no_warning() -> None:
    data = _minimal_kubeconfig()
    kube_config = KubeConfig.model_validate(data)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        await configure_from_kubeconfig(config=kube_config)


@pytest.mark.anyio
async def test_configure_bearer_token() -> None:
    data = _minimal_kubeconfig(token="my-secret-bearer-token")
    kube_config = KubeConfig.model_validate(data)
    client_config = await configure_from_kubeconfig(config=kube_config)
    assert client_config.token == "my-secret-bearer-token"


@pytest.mark.anyio
async def test_configure_token_file(tmp_path: Path) -> None:
    token_file = tmp_path / "token"
    token_file.write_text("token-from-file")
    data = _minimal_kubeconfig(token_file=str(token_file))
    config_file = _write_kubeconfig(tmp_path / "config", data)
    kube_config = _load_kube_config(config_file)
    client_config = await configure_from_kubeconfig(config=kube_config)
    assert client_config.token == "token-from-file"
    assert client_config.try_refresh_token is True


@pytest.mark.anyio
async def test_configure_exec_wires_refreshable_token() -> None:
    data = _minimal_kubeconfig()
    data["users"][0]["user"]["exec"] = {
        "apiVersion": "client.authentication.k8s.io/v1",
        "command": "echo",
        "args": [
            "-n",
            '{"apiVersion":"client.authentication.k8s.io/v1",'
            '"kind":"ExecCredential","status":{"token":"exec-token"}}',
        ],
    }
    kube_config = KubeConfig.model_validate(data)
    client_config = await configure_from_kubeconfig(config=kube_config)
    assert isinstance(client_config.refreshable_token, ExecRefreshableToken)
    assert await client_config.get_authorization_header() == "Bearer exec-token"


@pytest.mark.anyio
async def test_configure_oidc_wires_refreshable_token() -> None:
    data = _minimal_kubeconfig()
    data["users"][0]["user"]["auth-provider"] = {
        "name": "oidc",
        "config": {
            "client-id": "id",
            "client-secret": "secret",
            "refresh-token": "token",
            "idp-issuer-url": "https://issuer.example",
        },
    }
    kube_config = KubeConfig.model_validate(data)
    client_config = await configure_from_kubeconfig(config=kube_config)
    assert isinstance(client_config.refreshable_token, OidcRefreshableToken)


@pytest.mark.anyio
async def test_configure_unsupported_auth_provider_raises_configuration_error() -> None:
    data = _minimal_kubeconfig()
    data["users"][0]["user"]["auth-provider"] = {
        "name": "gcp",
        "config": {"access-token": "abc"},
    }
    kube_config = KubeConfig.model_validate(data)
    with pytest.raises(ConfigurationError, match="'gcp' auth-provider"):
        await configure_from_kubeconfig(config=kube_config)


@pytest.mark.anyio
async def test_configure_invalid_oidc_config_raises_configuration_error() -> None:
    data = _minimal_kubeconfig()
    data["users"][0]["user"]["auth-provider"] = {
        "name": "oidc",
        "config": {"idp-issuer-url": "https://issuer.example"},
    }
    kube_config = KubeConfig.model_validate(data)
    with pytest.raises(ConfigurationError, match="'oidc' auth-provider"):
        await configure_from_kubeconfig(config=kube_config)


@pytest.mark.anyio
async def test_configure_forwards_impersonation_tls_server_name_and_basic_auth() -> (
    None
):
    raw = _minimal_kubeconfig()
    raw["clusters"][0]["cluster"]["tls-server-name"] = "kubernetes.default"
    raw["users"][0]["user"].update(
        {
            "username": "admin",
            "password": "pw",
            "as": "jane",
            "as-uid": "42",
            "as-groups": ["dev"],
            "as-user-extra": {"scopes": ["view", "edit"]},
        }
    )
    config = await configure_from_kubeconfig(KubeConfig.model_validate(raw))
    assert config.tls_server_name == "kubernetes.default"
    assert config.impersonation_headers == [
        ("Impersonate-User", "jane"),
        ("Impersonate-Uid", "42"),
        ("Impersonate-Group", "dev"),
        ("Impersonate-Extra-scopes", "view"),
        ("Impersonate-Extra-scopes", "edit"),
    ]
    assert (await config.get_authorization_header()) == "Basic YWRtaW46cHc="


# --- lenient loading: only the selected context is validated ---------------


def _stale_entries_kubeconfig(tmp_path: Path) -> dict[str, Any]:
    data = _minimal_kubeconfig(token="good-token")
    data["clusters"] += [
        {
            "name": "old-minikube",
            "cluster": {
                "server": "https://192.168.49.2:8443",
                "certificate-authority": str(tmp_path / "gone" / "ca.crt"),
            },
        },
        {"name": "empty-server", "cluster": {"server": ""}},
        {"name": "no-cluster-block"},
    ]
    data["users"] += [
        {
            "name": "old-minikube",
            "user": {
                "client-certificate": str(tmp_path / "gone" / "client.crt"),
                "client-key": str(tmp_path / "gone" / "client.key"),
                "tokenFile": str(tmp_path / "gone" / "token"),
            },
        },
        {
            "name": "legacy-exec",
            "user": {
                "exec": {
                    "apiVersion": "client.authentication.k8s.io/v1alpha1",
                    "command": "old-plugin",
                }
            },
        },
    ]
    data["contexts"] += [
        {
            "name": "old-minikube",
            "context": {"cluster": "old-minikube", "user": "old-minikube"},
        },
        {"name": "half-context", "context": {}},
    ]
    return data


@pytest.mark.anyio
async def test_stale_unrelated_entries_do_not_break_loading(tmp_path: Path) -> None:
    config_file = _write_kubeconfig(
        tmp_path / "config", _stale_entries_kubeconfig(tmp_path)
    )
    client_config = await configure_from_kubeconfig(config_file=config_file)
    assert client_config.base_url == "https://localhost:6443"
    assert await client_config.get_authorization_header() == "Bearer good-token"


@pytest.mark.anyio
async def test_selecting_stale_context_reports_missing_file(tmp_path: Path) -> None:
    config_file = _write_kubeconfig(
        tmp_path / "config", _stale_entries_kubeconfig(tmp_path)
    )
    with pytest.raises(ConfigurationError) as exc_info:
        await configure_from_kubeconfig(
            config_file=config_file, use_context="old-minikube"
        )
    message = str(exc_info.value)
    assert "certificate-authority" in message
    assert str(tmp_path / "gone" / "ca.crt") in message


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("kwarg", "field"),
    [
        ("ca_file", "certificate-authority"),
        ("client_cert_file", "client-certificate"),
        ("client_key_file", "client-key"),
        ("token_file", "tokenFile"),
    ],
)
async def test_selected_missing_file_raises_configuration_error(
    tmp_path: Path, kwarg: str, field: str
) -> None:
    missing = tmp_path / "missing.pem"
    data = _minimal_kubeconfig(**{kwarg: str(missing)})  # type: ignore[arg-type]
    kube_config = KubeConfig.model_validate(data)
    with pytest.raises(ConfigurationError, match=field) as exc_info:
        await configure_from_kubeconfig(kube_config)
    assert str(missing) in str(exc_info.value)
    # Not a FileNotFoundError: create_client() would then silently fall back
    # to in-cluster configuration.
    assert not isinstance(exc_info.value, FileNotFoundError)


@pytest.mark.anyio
async def test_unused_token_file_is_not_required(tmp_path: Path) -> None:
    data = _minimal_kubeconfig(token="inline", token_file=str(tmp_path / "missing"))
    client_config = await configure_from_kubeconfig(KubeConfig.model_validate(data))
    assert await client_config.get_authorization_header() == "Bearer inline"


@pytest.mark.anyio
async def test_blank_path_fields_are_treated_as_unset(tmp_path: Path) -> None:
    data = _minimal_kubeconfig(ca_file="", client_cert_file="", token_file="")
    config_file = _write_kubeconfig(tmp_path / "config", data)
    client_config = await configure_from_kubeconfig(config_file=config_file)
    assert client_config.server_ca_file is None
    assert client_config.client_cert_file is None
    assert client_config.token_file is None


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("server", "expected"),
    [
        ("10.0.0.1:6443", "https://10.0.0.1:6443"),
        ("localhost:6443", "https://localhost:6443"),
        ("[fd00::1]:6443", "https://[fd00::1]:6443"),
        ("api.example.com", "https://api.example.com"),
        ("http://api.example.com:8080", "http://api.example.com:8080"),
        (
            "https://api.example.com/k8s/clusters/c-1/",
            "https://api.example.com/k8s/clusters/c-1/",
        ),
    ],
)
async def test_server_scheme_defaults_to_https(server: str, expected: str) -> None:
    data = _minimal_kubeconfig(server=server)
    client_config = await configure_from_kubeconfig(KubeConfig.model_validate(data))
    assert client_config.base_url == expected


@pytest.mark.anyio
@pytest.mark.parametrize("server", ["", "ftp://h:21", "https://h:notaport", "https://"])
async def test_invalid_selected_server_raises_configuration_error(server: str) -> None:
    data = _minimal_kubeconfig(server=server)
    with pytest.raises(ConfigurationError, match="server"):
        await configure_from_kubeconfig(KubeConfig.model_validate(data))


@pytest.mark.parametrize(
    "server",
    [
        "https://h:6443",
        "https://h:6443/",
        "h:6443",
        "https://h:6443/gateway",
        "https://h:6443/gateway/",
    ],
)
@pytest.mark.anyio
async def test_server_url_reaches_same_path_with_both_clients(server: str) -> None:
    # `str(HttpUrl)` used to add a trailing slash; both backends must resolve
    # request paths identically with or without one, and keep a path prefix.
    httpx_client_module = pytest.importorskip("kubex.client.httpx")
    aiohttp_client_module = pytest.importorskip("kubex.client.aiohttp")
    data = _minimal_kubeconfig(server=server, insecure_skip_tls_verify=True)
    client_config = await configure_from_kubeconfig(KubeConfig.model_validate(data))
    expected_prefix = "/gateway" if "gateway" in server else ""
    expected = f"https://h:6443{expected_prefix}/api/v1/namespaces"

    httpx_client = httpx_client_module.HttpxClient(client_config)
    try:
        request = httpx_client._inner_client.build_request("GET", "/api/v1/namespaces")
        assert str(request.url) == expected
    finally:
        await httpx_client._inner_client.aclose()

    origin, prefix = aiohttp_client_module._split_base_url(str(client_config.base_url))
    assert f"{origin}{prefix}/api/v1/namespaces" == expected


@pytest.mark.anyio
async def test_context_without_user_is_anonymous() -> None:
    data = _minimal_kubeconfig()
    data["users"] = []
    del data["contexts"][0]["context"]["user"]
    client_config = await configure_from_kubeconfig(KubeConfig.model_validate(data))
    assert await client_config.get_authorization_header() is None


@pytest.mark.anyio
async def test_context_without_cluster_raises_configuration_error() -> None:
    data = _minimal_kubeconfig()
    del data["contexts"][0]["context"]["cluster"]
    with pytest.raises(ConfigurationError, match="does not name a cluster"):
        await configure_from_kubeconfig(KubeConfig.model_validate(data))


@pytest.mark.anyio
async def test_basic_auth_username_without_password_sends_empty_password() -> None:
    data = _minimal_kubeconfig()
    data["users"][0]["user"]["username"] = "admin"
    client_config = await configure_from_kubeconfig(KubeConfig.model_validate(data))
    # base64("admin:")
    assert await client_config.get_authorization_header() == "Basic YWRtaW46"


# --- config_file= -----------------------------------------------------------


@pytest.mark.anyio
@pytest.mark.parametrize("as_str", [True, False])
async def test_config_file_resolves_paths_relative_to_the_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, as_str: bool
) -> None:
    kube_dir = tmp_path / "kube"
    kube_dir.mkdir()
    (kube_dir / "ca.crt").write_text("right-ca")
    config_file = _write_kubeconfig(
        kube_dir / "my-config", _minimal_kubeconfig(ca_file="ca.crt")
    )
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "ca.crt").write_text("wrong-ca-from-cwd")
    monkeypatch.chdir(elsewhere)

    client_config = await configure_from_kubeconfig(
        config_file=str(config_file) if as_str else config_file
    )
    assert client_config.server_ca_file is not None
    assert client_config.server_ca_file.read_text() == "right-ca"


@pytest.mark.anyio
async def test_config_file_relative_to_cwd_and_use_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = _minimal_kubeconfig()
    data["contexts"].append(
        {
            "name": "staging",
            "context": {
                "cluster": "test-cluster",
                "user": "test-user",
                "namespace": "stage",
            },
        }
    )
    _write_kubeconfig(tmp_path / "config", data)
    monkeypatch.chdir(tmp_path)
    client_config = await configure_from_kubeconfig(
        use_context="staging", config_file="config"
    )
    assert client_config.namespace == "stage"


@pytest.mark.anyio
async def test_config_file_ignores_kubeconfig_env(tmp_path: Path) -> None:
    other = _write_kubeconfig(
        tmp_path / "other", _minimal_kubeconfig(server="https://other:6443")
    )
    chosen = _write_kubeconfig(
        tmp_path / "chosen", _minimal_kubeconfig(server="https://chosen:6443")
    )
    with patch.dict("os.environ", {KUBECONFIG_ENV_VARIABLE: str(other)}):
        client_config = await configure_from_kubeconfig(config_file=chosen)
    assert client_config.base_url == "https://chosen:6443"


@pytest.mark.anyio
async def test_config_and_config_file_are_mutually_exclusive(tmp_path: Path) -> None:
    config_file = _write_kubeconfig(tmp_path / "config", _minimal_kubeconfig())
    with pytest.raises(ValueError, match="not both"):
        await configure_from_kubeconfig(
            KubeConfig.model_validate(_minimal_kubeconfig()), config_file=config_file
        )


@pytest.mark.anyio
async def test_missing_config_file_raises_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        await configure_from_kubeconfig(config_file=tmp_path / "nope")


# --- secrets stay out of errors and reprs ----------------------------------


def test_invalid_kubeconfig_error_names_entry_without_leaking_secrets(
    tmp_path: Path,
) -> None:
    data = _minimal_kubeconfig(token="SUPER-SECRET-TOKEN")
    data["users"].append(
        {
            "name": "broken",
            "user": {"token": "OTHER-SECRET", "as-groups": "not-a-list"},
        }
    )
    config_file = _write_kubeconfig(tmp_path / "config", data)
    with pytest.raises(ConfigurationError) as exc_info:
        _load_kube_config(config_file)
    message = str(exc_info.value)
    assert "users['broken'].user.as-groups" in message
    assert "SUPER-SECRET-TOKEN" not in message
    assert "OTHER-SECRET" not in message
    assert exc_info.value.__cause__ is None
    assert exc_info.value.__suppress_context__


def test_invalid_yaml_error_does_not_quote_the_file(tmp_path: Path) -> None:
    config_file = tmp_path / "config"
    config_file.write_text("users:\n- name: u\n  user:\n    token: SECRET: oops\n")
    with pytest.raises(ConfigurationError, match="line 4") as exc_info:
        _load_kube_config(config_file)
    assert "SECRET" not in str(exc_info.value)
    assert exc_info.value.__cause__ is None


@pytest.mark.parametrize(
    ("value", "error_class"),
    [
        pytest.param("!SECRET_VALUE", "ConstructorError", id="unknown-tag"),
        pytest.param("*SECRET_VALUE", "ComposerError", id="undefined-alias"),
    ],
)
def test_invalid_yaml_error_omits_interpolated_input(
    tmp_path: Path, value: str, error_class: str
) -> None:
    # These PyYAML errors copy the offending tag/alias into their `problem` text.
    config_file = tmp_path / "config"
    config_file.write_text(f"users:\n- name: u\n  user:\n    password: {value}\n")
    with pytest.raises(ConfigurationError, match="line 4") as exc_info:
        _load_kube_config(config_file)
    message = str(exc_info.value)
    assert "SECRET_VALUE" not in message
    assert error_class in message
    assert exc_info.value.__cause__ is None


def test_auth_info_repr_hides_secrets() -> None:
    data = _minimal_kubeconfig(
        token="TOKEN-VALUE", client_key_data=b64encode(b"KEY-VALUE").decode()
    )
    data["users"][0]["user"]["exec"] = {
        "apiVersion": "client.authentication.k8s.io/v1",
        "command": "plugin",
        "args": ["--client-secret=ARG-SECRET"],
        "env": [{"name": "API_KEY", "value": "ENV-SECRET"}],
    }
    config = KubeConfig.model_validate(data)
    rendered = repr(config)
    assert "TOKEN-VALUE" not in rendered
    assert b64encode(b"KEY-VALUE").decode() not in rendered
    assert "ENV-SECRET" not in rendered
    assert "ARG-SECRET" not in rendered


@pytest.mark.anyio
async def test_kubeconfig_token_file_wins_over_inline_token(tmp_path: Path) -> None:
    token_path = tmp_path / "token"
    token_path.write_text("file-token")
    data = _minimal_kubeconfig(token="inline-token", token_file=str(token_path))
    config_file = _write_kubeconfig(tmp_path / "config", data)
    client_config = await configure_from_kubeconfig(config_file=config_file)
    assert client_config.token == "file-token"


def test_exec_cluster_info_repr_hides_extension_config() -> None:
    cluster = ExecCredentialCluster(
        server="https://example.com", config={"apiKey": "EXT-SECRET"}
    )
    assert "EXT-SECRET" not in repr(cluster)


@pytest.mark.anyio
async def test_invalid_base64_data_reports_field_without_value() -> None:
    data = _minimal_kubeconfig(client_key_data="not=valid=base64")
    with pytest.raises(ConfigurationError, match="client-key-data") as exc_info:
        await configure_from_kubeconfig(KubeConfig.model_validate(data))
    assert "not=valid=base64" not in str(exc_info.value)


# --- exec command resolution ------------------------------------------------


def _exec_kubeconfig(command: str, **exec_fields: Any) -> dict[str, Any]:
    data = _minimal_kubeconfig()
    data["users"][0]["user"]["exec"] = {
        "apiVersion": "client.authentication.k8s.io/v1",
        "command": command,
        "interactiveMode": "Never",
        **exec_fields,
    }
    return data


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("./bin/plugin", "{dir}/bin/plugin"),
        ("bin/plugin", "{dir}/bin/plugin"),
        ("aws", "aws"),
        ("/usr/local/bin/plugin", "/usr/local/bin/plugin"),
    ],
)
def test_exec_command_with_separator_resolves_against_kubeconfig_dir(
    tmp_path: Path, command: str, expected: str
) -> None:
    config_file = _write_kubeconfig(tmp_path / "config", _exec_kubeconfig(command))
    config = _load_kube_config(config_file)
    exec_config = config.users[0].auth_info.exec
    assert exec_config is not None
    assert exec_config.command == expected.format(dir=tmp_path.resolve())


@pytest.mark.anyio
@pytest.mark.skipif(sys.platform == "win32", reason="POSIX shell script plugin")
async def test_relative_exec_command_runs_from_any_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kube_dir = tmp_path / "kube"
    (kube_dir / "bin").mkdir(parents=True)
    plugin = kube_dir / "bin" / "plugin.sh"
    plugin.write_text(
        "#!/bin/sh\n"
        'echo \'{"apiVersion":"client.authentication.k8s.io/v1",'
        '"kind":"ExecCredential","status":{"token":"relative-ok"}}\'\n'
    )
    plugin.chmod(0o755)
    config_file = _write_kubeconfig(
        kube_dir / "config", _exec_kubeconfig("./bin/plugin.sh")
    )
    monkeypatch.chdir(tmp_path)
    client_config = await configure_from_kubeconfig(config_file=config_file)
    assert await client_config.get_authorization_header() == "Bearer relative-ok"


@pytest.mark.anyio
async def test_exec_without_api_version_fails_at_configure_time() -> None:
    data = _exec_kubeconfig("plugin")
    del data["users"][0]["user"]["exec"]["apiVersion"]
    with pytest.raises(ConfigurationError, match="apiVersion"):
        await configure_from_kubeconfig(KubeConfig.model_validate(data))


@pytest.mark.anyio
async def test_provide_cluster_info_is_built_from_selected_cluster(
    tmp_path: Path,
) -> None:
    ca_file = tmp_path / "ca.crt"
    ca_file.write_bytes(b"CA-PEM")
    data = _exec_kubeconfig("plugin", provideClusterInfo=True)
    data["clusters"][0]["cluster"].update(
        {
            "server": "api.example.com:6443",
            "certificate-authority": str(ca_file),
            "tls-server-name": "kubernetes",
            "extensions": [
                {"name": "unrelated", "extension": {"x": 1}},
                {
                    "name": "client.authentication.k8s.io/exec",
                    "extension": {"audience": "kubex"},
                },
            ],
        }
    )
    client_config = await configure_from_kubeconfig(KubeConfig.model_validate(data))
    token_source = client_config.refreshable_token
    assert isinstance(token_source, ExecRefreshableToken)
    cluster_info = token_source._provider.cluster_info
    assert cluster_info is not None
    assert cluster_info.model_dump(by_alias=True, exclude_none=True) == {
        "server": "https://api.example.com:6443",
        "tls-server-name": "kubernetes",
        "certificate-authority-data": b64encode(b"CA-PEM").decode(),
        "config": {"audience": "kubex"},
    }


@pytest.mark.anyio
async def test_cluster_info_not_built_without_provide_cluster_info() -> None:
    client_config = await configure_from_kubeconfig(
        KubeConfig.model_validate(_exec_kubeconfig("plugin"))
    )
    token_source = client_config.refreshable_token
    assert isinstance(token_source, ExecRefreshableToken)
    assert token_source._provider.cluster_info is None


# --- OIDC ---------------------------------------------------------------------


def _oidc_kubeconfig(**config: str) -> dict[str, Any]:
    data = _minimal_kubeconfig()
    data["users"][0]["user"]["auth-provider"] = {
        "name": "oidc",
        "config": {
            "client-id": "kubernetes",
            "idp-issuer-url": "https://issuer.example",
            **config,
        },
    }
    return data


def _jwt_with_exp(exp: int) -> str:
    def segment(payload: dict[str, Any]) -> str:
        return urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()

    return f"{segment({'alg': 'none'})}.{segment({'exp': exp})}.sig"


@pytest.mark.anyio
async def test_oidc_public_client_with_id_token_only() -> None:
    id_token = _jwt_with_exp(int(time.time()) + 3600)
    data = _oidc_kubeconfig(**{"id-token": id_token})
    client_config = await configure_from_kubeconfig(KubeConfig.model_validate(data))
    # No refresh-token/client-secret and no network access needed.
    assert await client_config.get_authorization_header() == f"Bearer {id_token}"


@pytest.mark.anyio
async def test_oidc_expired_id_token_without_refresh_token_fails_clearly() -> None:
    data = _oidc_kubeconfig(**{"id-token": _jwt_with_exp(1_000)})
    client_config = await configure_from_kubeconfig(KubeConfig.model_validate(data))
    with pytest.raises(ConfigurationError, match="no refresh-token"):
        await client_config.get_authorization_header()


def test_oidc_idp_certificate_authority_resolves_against_kubeconfig_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_file = _write_kubeconfig(
        tmp_path / "config",
        _oidc_kubeconfig(**{"idp-certificate-authority": "idp-ca.pem"}),
    )
    monkeypatch.chdir("/")
    config = _load_kube_config(config_file)
    auth_provider = config.users[0].auth_info.auth_provider
    assert auth_provider is not None
    assert isinstance(auth_provider.config, dict)
    assert auth_provider.config["idp-certificate-authority"] == str(
        tmp_path.resolve() / "idp-ca.pem"
    )


@pytest.mark.anyio
async def test_oidc_missing_idp_certificate_authority_file(tmp_path: Path) -> None:
    missing = tmp_path / "idp-ca.pem"
    data = _oidc_kubeconfig(
        **{"idp-certificate-authority": str(missing), "refresh-token": "r"}
    )
    with pytest.raises(ConfigurationError, match="idp-certificate-authority"):
        await configure_from_kubeconfig(KubeConfig.model_validate(data))


def test_kubeconfig_models_drop_unknown_keys() -> None:
    """Resource models keep unknown fields; kubeconfig models must not (reprs)."""
    raw = _minimal_kubeconfig(token="tok")
    raw["users"][0]["user"]["mystery-secret"] = "do-not-show"
    config = KubeConfig.model_validate(raw)
    user = config.users[0].auth_info
    assert user.model_extra is None or user.model_extra == {}
    assert "do-not-show" not in repr(config)


def test_numeric_credentials_in_unused_user_do_not_break_loading() -> None:
    raw = _minimal_kubeconfig(token="tok")
    raw["users"].append(
        {"name": "legacy-basic", "user": {"username": "admin", "password": 123456}}
    )
    config = KubeConfig.model_validate(raw)
    legacy = config.users[1].auth_info
    assert legacy.password is not None
    assert legacy.password.get_secret_value() == "123456"
