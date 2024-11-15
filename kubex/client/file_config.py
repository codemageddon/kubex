import atexit
import os
from base64 import b64decode
from pathlib import Path
from tempfile import NamedTemporaryFile

from yaml import safe_load

from .configuration import ClientConfiguration, KubeConfig

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


def _get_kube_config_file() -> Path:
    """Returns the path to the kubeconfig file."""
    kube_config_path = os.environ.get(KUBECONFIG_ENV_VARIABLE)
    if kube_config_path:
        return Path(kube_config_path).resolve()
    return DEFAULT_KUBE_CONFIG_FILE


def _load_kube_config(config_file: Path | None = None) -> KubeConfig:
    if not config_file:
        config_file = _get_kube_config_file()
    config_content = config_file.read_text()
    return KubeConfig.model_validate(safe_load(config_content))


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
    return ClientConfiguration(
        url=str(cluster.server),
        server_ca_file=ca_file,
        client_cert_file=client_cert_file,
        client_key_file=client_key_file,
    )


def _decode_and_put_to_file(data: str) -> Path:
    if len(_temp_files) == 0:
        atexit.register(_cleanup_temp_files)
    if data in _temp_files:
        return _temp_files[data]
    decoded = b64decode(data)
    with NamedTemporaryFile(delete=False, delete_on_close=False) as f:
        f.write(decoded)
        path = Path(f.name)
        _temp_files[data] = path
        return path
