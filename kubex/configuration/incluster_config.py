import os
from pathlib import Path

from kubex.core.exceptions import ConfigurationError

from .configuration import ClientConfiguration

KUBERNETES_SERVICE_HOST_ENV = "KUBERNETES_SERVICE_HOST"
KUBERNETES_SERVICE_PORT_ENV = "KUBERNETES_SERVICE_PORT"
DEFAULT_TOKEN_FILENAME = Path("/var/run/secrets/kubernetes.io/serviceaccount/token")
DEFAULT_CERT_FILENAME = Path("/var/run/secrets/kubernetes.io/serviceaccount/ca.crt")
DEFAULT_NAMESAPCE_FILENAME = Path(
    "/var/run/secrets/kubernetes.io/serviceaccount/namespace"
)
DEFAULT_NAMESPACE = "default"


def _join_host_port(host: str, port: str) -> str:
    """`host:port`, bracketing IPv6 literals like Go's `net.JoinHostPort`."""
    if ":" in host and not host.startswith("["):
        return f"[{host}]:{port}"
    return f"{host}:{port}"


def _read_namespace() -> str:
    # client-go falls back to "default" when the service-account namespace
    # file is absent (e.g. automountServiceAccountToken: false).
    try:
        namespace = DEFAULT_NAMESAPCE_FILENAME.read_text().strip()
    except OSError:
        return DEFAULT_NAMESPACE
    return namespace or DEFAULT_NAMESPACE


async def configure_from_pod_env(
    token_filename: Path | None = None,
    cert_filename: Path | None = None,
    kubernetes_service_host: str | None = None,
    kubernetes_service_port: str | None = None,
    try_refresh_token: bool = True,
) -> ClientConfiguration:
    """Build a ClientConfiguration from the pod's service-account mount.

    Raises:
        ConfigurationError: `KUBERNETES_SERVICE_HOST`/`KUBERNETES_SERVICE_PORT`
            are not set (and not passed explicitly), i.e. the process is not
            running inside a cluster.
    """
    if token_filename is None:
        token_filename = DEFAULT_TOKEN_FILENAME
    if cert_filename is None:
        cert_filename = DEFAULT_CERT_FILENAME
    if kubernetes_service_host is None:
        kubernetes_service_host = os.environ.get(KUBERNETES_SERVICE_HOST_ENV)
    if kubernetes_service_port is None:
        kubernetes_service_port = os.environ.get(KUBERNETES_SERVICE_PORT_ENV)
    if not kubernetes_service_host or not kubernetes_service_port:
        raise ConfigurationError(
            "Unable to load in-cluster configuration: not running inside a "
            f"Kubernetes cluster ({KUBERNETES_SERVICE_HOST_ENV} and "
            f"{KUBERNETES_SERVICE_PORT_ENV} are not set). Outside a cluster, "
            "provide a kubeconfig file (~/.kube/config or $KUBECONFIG)."
        )
    return ClientConfiguration(
        url=f"https://{_join_host_port(kubernetes_service_host, kubernetes_service_port)}",
        server_ca_file=cert_filename,
        client_cert_file=None,
        client_key_file=None,
        namespace=_read_namespace(),
        token_file=token_filename,
        try_refresh_token=try_refresh_token,
    )
