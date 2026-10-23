from __future__ import annotations

from collections.abc import Generator
from typing import Any

import atexit
import os
import warnings
from base64 import b64encode
from pathlib import Path
from unittest.mock import patch

import pytest
from yaml import dump

from kubex.configuration.auth.refreshable_token import (
    ExecRefreshableToken,
    OidcRefreshableToken,
)
from kubex.configuration.configuration import KubeConfig
from kubex.core.exceptions import ConfigurationError

from kubex.configuration.file_config import (
    DEFAULT_KUBE_CONFIG_FILE,
    KUBECONFIG_ENV_VARIABLE,
    _cleanup_temp_files,
    _decode_and_put_to_file,
    _get_kube_config_file,
    _get_kube_config_files,
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
    assert str(config.clusters[0].cluster.server) == "https://custom:8443/"


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
    assert str(config.clusters[0].cluster.server) == "https://first:6443/"


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
    assert client_config.base_url == "https://localhost:6443/"


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
async def test_configure_from_kubeconfig_no_context_namespace_stays_none(
    tmp_path: Path,
) -> None:
    data = _minimal_kubeconfig()
    config_file = _write_kubeconfig(tmp_path / "config", data)
    kube_config = _load_kube_config(config_file)
    client_config = await configure_from_kubeconfig(config=kube_config)
    assert client_config.namespace is None


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
