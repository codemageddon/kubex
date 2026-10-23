import atexit
import os
import warnings
from base64 import b64decode
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from pydantic import ValidationError
from yaml import safe_load

from kubex.core.exceptions import ConfigurationError

from .auth.exec import ExecAuthProvider
from .auth.oidc import OIDCAuthProvider
from .auth.refreshable_token import ExecRefreshableToken, OidcRefreshableToken
from .configuration import (
    ClientConfiguration,
    KubeConfig,
    OIDCConfig,
    SupportsAuthorizationHeader,
)

DEFAULT_KUBE_CONFIG_FILE = Path.home() / ".kube" / "config"
KUBECONFIG_ENV_VARIABLE = "KUBECONFIG"

_temp_files: dict[str, Path] = {}


def _cleanup_temp_files() -> None:
    global _temp_files
    for temp_file in _temp_files.values():
        try:
            temp_file.unlink(missing_ok=True)
        except Exception:
            continue


def _get_kube_config_files() -> list[Path]:
    """Returns the kubeconfig file(s) to load"""
    kube_config_path = os.environ.get(KUBECONFIG_ENV_VARIABLE)
    if not kube_config_path:
        return [DEFAULT_KUBE_CONFIG_FILE]
    return [Path(part).resolve() for part in kube_config_path.split(os.pathsep) if part]


def _get_kube_config_file() -> Path:
    """Returns the path to the (first) kubeconfig file."""
    return _get_kube_config_files()[0]


_MERGED_LIST_KEYS = ("clusters", "users", "contexts")


def _merge_kube_config_dicts(raws: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge raw kubeconfig dicts using kubectl's `KUBECONFIG` precedence rules.

    `clusters`/`users`/`contexts` are unioned by `name`, with the first file's
    entry for a given name taking precedence over later files. Scalar fields
    (e.g. `current-context`) are taken from the first file that sets them.
    """
    merged: dict[str, Any] = {}
    seen_names: dict[str, set[str]] = {key: set() for key in _MERGED_LIST_KEYS}
    for raw in raws:
        for key, value in raw.items():
            if key in _MERGED_LIST_KEYS:
                merged_list = merged.setdefault(key, [])
                for item in value or []:
                    name = item.get("name") if isinstance(item, dict) else None
                    if name is not None and name in seen_names[key]:
                        continue
                    if name is not None:
                        seen_names[key].add(name)
                    merged_list.append(item)
            elif not merged.get(key):
                merged[key] = value
    return merged


_CLUSTER_PATH_FIELDS = ("certificate-authority",)
_USER_PATH_FIELDS = ("client-certificate", "client-key", "tokenFile")


def _resolve_path_field(value: Any, base_dir: Path) -> Any:
    if not isinstance(value, str) or Path(value).is_absolute():
        return value
    return str(base_dir / value)


def _resolve_relative_paths(raw: Any, base_dir: Path) -> Any:
    """Resolve cluster/user file-path fields in a raw kubeconfig dict against `base_dir`.

    Kubeconfig file-path fields (`certificate-authority`, `client-certificate`,
    `client-key`, `tokenFile`) are relative to the kubeconfig file itself (matching
    `kubectl`), not the process's current working directory. Pydantic's `FilePath`
    validates existence relative to cwd, so relative paths are rewritten here, before
    `KubeConfig.model_validate()` sees them.
    """
    if not isinstance(raw, dict):
        return raw
    for named_cluster in raw.get("clusters") or []:
        cluster = (
            named_cluster.get("cluster") if isinstance(named_cluster, dict) else None
        )
        if not isinstance(cluster, dict):
            continue
        for field in _CLUSTER_PATH_FIELDS:
            if field in cluster:
                cluster[field] = _resolve_path_field(cluster[field], base_dir)
    for named_user in raw.get("users") or []:
        user = named_user.get("user") if isinstance(named_user, dict) else None
        if not isinstance(user, dict):
            continue
        for field in _USER_PATH_FIELDS:
            if field in user:
                user[field] = _resolve_path_field(user[field], base_dir)
    return raw


def _load_kube_config(config_file: Path | None = None) -> KubeConfig:
    if config_file is not None:
        files = [config_file.resolve()]
    else:
        candidates = _get_kube_config_files()
        files = [f for f in candidates if f.exists()]
        if not files:
            # Preserve FileNotFoundError (rather than e.g. a merge of zero
            # files) so create_client()'s in-cluster fallback still triggers.
            raise FileNotFoundError(
                f"No kubeconfig file found; checked {[str(f) for f in candidates]}"
            )
    raws = [_resolve_relative_paths(safe_load(f.read_text()), f.parent) for f in files]
    dict_raws = []
    for file, raw in zip(files, raws):
        if raw is None:
            # An empty or comment-only file parses to None via yaml.safe_load();
            # treat that the same as a missing file rather than raising when
            # _merge_kube_config_dicts() sees a non-dict entry.
            continue
        if not isinstance(raw, dict):
            raise ConfigurationError(
                f"{file}: expected a kubeconfig mapping at the document root, "
                f"got {type(raw).__name__}"
            )
        dict_raws.append(raw)
    if not dict_raws:
        raise FileNotFoundError(
            f"No usable kubeconfig file found; checked {[str(f) for f in files]}"
        )
    merged = (
        dict_raws[0] if len(dict_raws) == 1 else _merge_kube_config_dicts(dict_raws)
    )
    return KubeConfig.model_validate(merged)


async def configure_from_kubeconfig(
    config: KubeConfig | None = None, use_context: str | None = None
) -> ClientConfiguration:
    """Creates a ClientConfiguration from a KubeConfig."""
    if config is None:
        config = _load_kube_config()
    current_context = use_context or config.current_context
    if not current_context:
        raise ValueError("No current context in kubeconfig")
    context = next(
        (c.context for c in config.contexts if c.name == current_context),
        None,
    )
    if not context:
        raise ValueError(f"Context {current_context} not found in kubeconfig")
    cluster = next(
        (c.cluster for c in config.clusters if c.name == context.cluster),
        None,
    )
    if not cluster:
        raise ValueError(f"Cluster {context.cluster} not found in kubeconfig")
    user = next(
        (u.auth_info for u in config.users if u.name == context.user),
        None,
    )
    if not user:
        raise ValueError(f"User {context.user} not found in kubeconfig")
    ca_file = cluster.certificate_authority
    if ca_file is None and cluster.certificate_authority_data is not None:
        ca_file = _decode_and_put_to_file(cluster.certificate_authority_data)
    client_cert_file = user.client_certificate
    if client_cert_file is None and user.client_certificate_data is not None:
        client_cert_file = _decode_and_put_to_file(user.client_certificate_data)
    client_key_file = user.client_key
    if client_key_file is None and user.client_key_data is not None:
        client_key_file = _decode_and_put_to_file(user.client_key_data)
    refreshable_token: SupportsAuthorizationHeader | None = None
    if user.exec is not None:
        refreshable_token = ExecRefreshableToken(ExecAuthProvider(user.exec))
    elif user.auth_provider is not None:
        if user.auth_provider.name != "oidc":
            raise ConfigurationError(
                f"configure_from_kubeconfig() does not support the "
                f"{user.auth_provider.name!r} auth-provider; only 'oidc' with a "
                "valid OIDC config is supported."
            )
        oidc_config = user.auth_provider.config
        # `AuthProviderConfig.config` is typed `OIDCConfig | dict[str, str]`, but
        # pydantic's smart union resolves hyphen-aliased YAML data to the `dict`
        # branch (an exact structural match) rather than `OIDCConfig` (which
        # needs alias resolution), so it is validated explicitly here instead
        # of relying on `isinstance`.
        if not isinstance(oidc_config, OIDCConfig):
            try:
                oidc_config = OIDCConfig.model_validate(oidc_config)
            except ValidationError as exc:
                # Don't interpolate `exc` directly: pydantic's error message embeds a
                # repr of the input dict, which is the raw oidc config block and may
                # contain `client-secret`/`refresh-token`. Report only the error
                # locations, and use `from None` so the input-bearing exception is
                # not chained into a logged traceback.
                error_locations = [
                    ".".join(str(part) for part in error["loc"])
                    for error in exc.errors()
                ]
                raise ConfigurationError(
                    "configure_from_kubeconfig(): invalid 'oidc' auth-provider "
                    f"config: {exc.error_count()} validation error(s) at "
                    f"{error_locations}"
                ) from None
        refreshable_token = OidcRefreshableToken(OIDCAuthProvider(oidc_config))
    if cluster.proxy_url:
        warnings.warn(
            f"kubeconfig cluster {context.cluster!r} sets proxy-url, which "
            "configure_from_kubeconfig() does not apply (it belongs on "
            "ClientOptions, which this function has no access to). Pass the "
            "equivalent proxy via ClientOptions(proxy=...) when constructing "
            "the client.",
            UserWarning,
            stacklevel=2,
        )
    return ClientConfiguration(
        url=str(cluster.server),
        server_ca_file=ca_file,
        # Cluster.insecure_skip_tls_verify defaults to False (not None), and
        # ClientConfiguration raises when insecure_skip_tls_verify is False
        # (rather than None) with no server_ca_file -- so only forward True,
        # leaving the common "no CA, no insecure flag" kubeconfig (system
        # trust store) as ClientConfiguration's own default of None.
        insecure_skip_tls_verify=True if cluster.insecure_skip_tls_verify else None,
        client_cert_file=client_cert_file,
        client_key_file=client_key_file,
        token=user.token,
        token_file=user.token_file,
        namespace=context.namespace,
        try_refresh_token=user.token_file is not None,
        refreshable_token=refreshable_token,
    )


def _decode_and_put_to_file(data: str) -> Path:
    if len(_temp_files) == 0:
        atexit.register(_cleanup_temp_files)
    if data in _temp_files:
        return _temp_files[data]
    decoded = b64decode(data)
    with NamedTemporaryFile(delete=False) as f:
        f.write(decoded)
        path = Path(f.name)
        _temp_files[data] = path
        return path
