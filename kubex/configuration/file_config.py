import atexit
import os
import warnings
from base64 import b64decode, b64encode
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, NamedTuple
from urllib.parse import urlsplit

from pydantic import ValidationError
from yaml import MarkedYAMLError, YAMLError, safe_load

from kubex.core.exceptions import ConfigurationError, ConfigurationValueError

from .auth.exec import ExecAuthProvider, ExecCredentialCluster
from .auth.oidc import OIDCAuthProvider
from .auth.refreshable_token import ExecRefreshableToken, OidcRefreshableToken
from .configuration import (
    AuthInfo,
    AuthProviderConfig,
    ClientConfiguration,
    Cluster,
    KubeConfig,
    OIDCConfig,
    SupportsAuthorizationHeader,
    describe_validation_error,
)

DEFAULT_KUBE_CONFIG_FILE = Path.home() / ".kube" / "config"
KUBECONFIG_ENV_VARIABLE = "KUBECONFIG"
DEFAULT_NAMESPACE = "default"
EXEC_CLUSTER_EXTENSION_NAME = "client.authentication.k8s.io/exec"


class _TempFile(NamedTuple):
    path: Path
    owner_pid: int


_temp_files: dict[str, _TempFile] = {}
"""Decoded `*-data` payload -> temp file holding it."""
_cleanup_registered = False


def _cleanup_temp_files() -> None:
    pid = os.getpid()
    for temp_file in list(_temp_files.values()):
        if temp_file.owner_pid != pid:
            # Inherited across fork(): the creating process still uses it.
            continue
        try:
            temp_file.path.unlink(missing_ok=True)
        except OSError:
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
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        return value
    return str(base_dir / value)


def _has_path_separator(command: str) -> bool:
    return os.sep in command or (os.altsep is not None and os.altsep in command)


def _resolve_relative_paths(raw: Any, base_dir: Path) -> Any:
    """Resolve file references in a raw kubeconfig dict against `base_dir`.

    Kubeconfig file-path fields (`certificate-authority`, `client-certificate`,
    `client-key`, `tokenFile`, the oidc `idp-certificate-authority`) are
    relative to the kubeconfig file itself (matching `kubectl`), not the
    process's current working directory. An exec `command` is resolved the
    same way only when it contains a path separator; a bare name stays a PATH
    lookup (client-go's rule).
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
        exec_config = user.get("exec")
        if isinstance(exec_config, dict):
            command = exec_config.get("command")
            if isinstance(command, str) and _has_path_separator(command):
                exec_config["command"] = _resolve_path_field(command, base_dir)
        auth_provider = user.get("auth-provider")
        if isinstance(auth_provider, dict) and auth_provider.get("name") == "oidc":
            provider_config = auth_provider.get("config")
            if (
                isinstance(provider_config, dict)
                and "idp-certificate-authority" in provider_config
            ):
                provider_config["idp-certificate-authority"] = _resolve_path_field(
                    provider_config["idp-certificate-authority"], base_dir
                )
    return raw


def _parse_yaml(file: Path) -> Any:
    try:
        return safe_load(file.read_text())
    except YAMLError as exc:
        # Only the position and error class: PyYAML's message quotes the
        # offending line, and its `problem` text interpolates input (tags,
        # anchors, characters), any of which may hold a secret.
        where = ""
        if isinstance(exc, MarkedYAMLError) and exc.problem_mark is not None:
            mark = exc.problem_mark
            where = f" at line {mark.line + 1}, column {mark.column + 1}"
        raise ConfigurationError(
            f"{file}: invalid kubeconfig YAML{where} ({type(exc).__name__})"
        ) from None


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
    raws = [_resolve_relative_paths(_parse_yaml(f), f.parent) for f in files]
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
    try:
        return KubeConfig.model_validate(merged)
    except ValidationError as exc:
        # `from None` and no `exc` text: pydantic's message embeds the input,
        # which may be a token or key.
        raise ConfigurationError(
            f"Invalid kubeconfig {[str(f) for f in files]}: "
            f"{describe_validation_error(exc, merged)}"
        ) from None


def _server_url(cluster_name: str, server: str | None) -> str:
    """Validate the selected cluster's `server`, defaulting a missing scheme to https."""
    if not server or not server.strip():
        raise ConfigurationError(
            f"kubeconfig cluster {cluster_name!r} has no server defined"
        )
    server = server.strip()
    if "://" not in server:
        # A bare `host:port` (client-go's DefaultServerURL rule).
        server = f"https://{server}"
    try:
        parsed = urlsplit(server)
        parsed.port  # raises ValueError for a malformed port
    except ValueError:
        parsed = None
    if parsed is None or parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ConfigurationError(
            f"kubeconfig cluster {cluster_name!r}: server {server!r} is not a valid "
            "http(s) URL"
        )
    return server


def _require_file(path: Path, owner: str, field: str) -> None:
    if not path.exists() or path.is_dir():
        raise ConfigurationError(
            f"kubeconfig {owner}: {field} file {str(path)!r} does not exist"
        )


def _data_or_file(
    data: str | None, path: Path | None, owner: str, field: str
) -> Path | None:
    """`<field>-data` overrides `<field>` (client-go); a used file must exist."""
    if data:
        try:
            return _decode_and_put_to_file(data)
        except ValueError:  # includes binascii.Error
            raise ConfigurationError(
                f"kubeconfig {owner}: {field}-data is not valid base64"
            ) from None
    if path is not None:
        _require_file(path, owner, field)
    return path


def _exec_cluster_info(
    server: str, cluster: Cluster, ca_file: Path | None
) -> ExecCredentialCluster:
    """`spec.cluster` for an exec plugin with `provideClusterInfo: true`."""
    return ExecCredentialCluster(
        server=server,
        tls_server_name=cluster.tls_server_name or None,
        insecure_skip_tls_verify=cluster.insecure_skip_tls_verify or None,
        certificate_authority_data=(
            b64encode(ca_file.read_bytes()).decode("ascii")
            if ca_file is not None
            else None
        ),
        proxy_url=cluster.proxy_url or None,
        disable_compression=cluster.disable_compression or None,
        config=next(
            (
                extension.extension
                for extension in cluster.extensions or []
                if extension.name == EXEC_CLUSTER_EXTENSION_NAME
            ),
            None,
        ),
    )


def _oidc_config(user_name: str, auth_provider: AuthProviderConfig) -> OIDCConfig:
    oidc_config = auth_provider.config
    # `AuthProviderConfig.config` is typed `OIDCConfig | dict[str, str]`, but
    # pydantic's smart union resolves hyphen-aliased YAML data to the `dict`
    # branch (an exact structural match) rather than `OIDCConfig` (which
    # needs alias resolution), so it is validated explicitly here instead
    # of relying on `isinstance`.
    if not isinstance(oidc_config, OIDCConfig):
        try:
            oidc_config = OIDCConfig.model_validate(oidc_config)
        except ValidationError as exc:
            # Only error locations: pydantic's message embeds the raw config
            # block, which may contain `client-secret`/`refresh-token`.
            raise ConfigurationError(
                "configure_from_kubeconfig(): invalid 'oidc' auth-provider "
                f"config: {describe_validation_error(exc)}"
            ) from None
    if (
        not oidc_config.idp_certificate_authority_data
        and oidc_config.idp_certificate_authority is not None
    ):
        _require_file(
            oidc_config.idp_certificate_authority,
            f"user {user_name!r}",
            "idp-certificate-authority",
        )
    return oidc_config


async def configure_from_kubeconfig(
    config: KubeConfig | None = None,
    use_context: str | None = None,
    *,
    config_file: str | os.PathLike[str] | None = None,
) -> ClientConfiguration:
    """Create a ClientConfiguration from a kubeconfig.

    Only the selected context's cluster and user are checked (server URL,
    referenced files), so a stale entry for another context does not matter.

    Args:
        config: An already-parsed kubeconfig. Relative file paths inside it are
            used as-is (relative to the current directory); use `config_file`
            to load a file from disk.
        use_context: Context to use instead of `current-context`.
        config_file: Kubeconfig file to load instead of `$KUBECONFIG` /
            `~/.kube/config`. Relative paths inside it resolve against its
            directory, as with kubectl.

    Raises:
        FileNotFoundError: No kubeconfig file exists.
        ConfigurationError: The kubeconfig, or the selected cluster/user, is
            invalid (e.g. a referenced certificate file is missing).
        ConfigurationValueError: The context, or the cluster/user it names, is
            not defined. Also a `ConfigurationError` and a `ValueError`.
        ValueError: Both `config` and `config_file` are given.
    """
    if config is not None and config_file is not None:
        raise ValueError("Pass either config or config_file, not both")
    if config is None:
        config = _load_kube_config(
            Path(config_file) if config_file is not None else None
        )
    current_context = use_context or config.current_context
    if not current_context:
        raise ConfigurationValueError("No current context in kubeconfig")
    context = next(
        (c.context for c in config.contexts if c.name == current_context),
        None,
    )
    if context is None:
        raise ConfigurationValueError(
            f"Context {current_context} not found in kubeconfig"
        )
    if not context.cluster:
        raise ConfigurationError(
            f"kubeconfig context {current_context!r} does not name a cluster"
        )
    cluster = next(
        (c.cluster for c in config.clusters if c.name == context.cluster),
        None,
    )
    if cluster is None:
        raise ConfigurationValueError(
            f"Cluster {context.cluster} not found in kubeconfig"
        )
    user = AuthInfo()
    if context.user:
        found_user = next(
            (u.auth_info for u in config.users if u.name == context.user),
            None,
        )
        if found_user is None:
            raise ConfigurationValueError(
                f"User {context.user} not found in kubeconfig"
            )
        user = found_user
    cluster_owner = f"cluster {context.cluster!r}"
    user_owner = f"user {context.user!r}"
    server = _server_url(context.cluster, cluster.server)
    ca_file = _data_or_file(
        cluster.certificate_authority_data,
        cluster.certificate_authority,
        cluster_owner,
        "certificate-authority",
    )
    client_cert_file = _data_or_file(
        user.client_certificate_data,
        user.client_certificate,
        user_owner,
        "client-certificate",
    )
    client_key_file = _data_or_file(
        user.client_key_data, user.client_key, user_owner, "client-key"
    )
    if user.token_file is not None and not user.token:
        _require_file(user.token_file, user_owner, "tokenFile")
    refreshable_token: SupportsAuthorizationHeader | None = None
    if user.exec is not None:
        cluster_info = (
            _exec_cluster_info(server, cluster, ca_file)
            if user.exec.provide_cluster_info
            else None
        )
        refreshable_token = ExecRefreshableToken(
            ExecAuthProvider(user.exec, cluster_info=cluster_info)
        )
    elif user.auth_provider is not None:
        if user.auth_provider.name != "oidc":
            raise ConfigurationError(
                f"configure_from_kubeconfig() does not support the "
                f"{user.auth_provider.name!r} auth-provider; only 'oidc' with a "
                "valid OIDC config is supported."
            )
        refreshable_token = OidcRefreshableToken(
            OIDCAuthProvider(_oidc_config(context.user or "", user.auth_provider))
        )
    # Basic auth needs a username; client-go sends an empty password if unset.
    username = user.username or None
    password = None
    if username is not None:
        password = user.password.get_secret_value() if user.password else ""
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
        url=server,
        server_ca_file=ca_file,
        # Cluster.insecure_skip_tls_verify defaults to False (not None), and
        # ClientConfiguration raises when insecure_skip_tls_verify is False
        # (rather than None) with no server_ca_file -- so only forward True,
        # leaving the common "no CA, no insecure flag" kubeconfig (system
        # trust store) as ClientConfiguration's own default of None.
        insecure_skip_tls_verify=True if cluster.insecure_skip_tls_verify else None,
        client_cert_file=client_cert_file,
        client_key_file=client_key_file,
        token=user.token or None,
        token_file=user.token_file,
        # kubectl/client-go use "default" when the context sets no namespace.
        namespace=context.namespace or DEFAULT_NAMESPACE,
        try_refresh_token=user.token_file is not None,
        refreshable_token=refreshable_token,
        tls_server_name=cluster.tls_server_name,
        username=username,
        password=password,
        impersonate_user=user.as_,
        impersonate_uid=user.as_uid,
        impersonate_groups=user.as_groups,
        impersonate_extra=user.as_user_extra,
    )


def _decode_and_put_to_file(data: str) -> Path:
    """Write base64 `data` to a private temp file (cached per payload).

    The file is re-created if it has been deleted since, and removed at exit
    only by the process that created it.
    """
    global _cleanup_registered
    cached = _temp_files.get(data)
    if cached is not None and cached.path.exists():
        return cached.path
    # Line breaks are tolerated (as by Go's decoder); other junk is an error.
    decoded = b64decode("".join(data.split()), validate=True)
    if not _cleanup_registered:
        atexit.register(_cleanup_temp_files)
        _cleanup_registered = True
    with NamedTemporaryFile(delete=False) as f:
        f.write(decoded)
    path = Path(f.name)
    _temp_files[data] = _TempFile(path, os.getpid())
    return path
