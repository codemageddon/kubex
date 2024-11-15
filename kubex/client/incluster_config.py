import os
from pathlib import Path

from .configuration import ClientConfiguration

KUBERNETES_SERVICE_HOST_ENV = "KUBERNETES_SERVICE_HOST"
KUBERNETES_SERVICE_PORT_ENV = "KUBERNETES_SERVICE_PORT"
DEFAULT_TOKEN_FILENAME = Path("/var/run/secrets/kubernetes.io/serviceaccount/token")
DEFAULT_CERT_FILENAME = Path("/var/run/secrets/kubernetes.io/serviceaccount/ca.crt")
DEFAULT_NAMESAPCE_FILENAME = Path(
    "/var/run/secrets/kubernetes.io/serviceaccount/namespace"
)


async def configure_from_pod_env(
    token_filename: Path | None = None,
    cert_filename: Path | None = None,
    kubernetes_service_host: str | None = None,
    kubernetes_service_port: str | None = None,
    try_refresh_token: bool = True,
) -> ClientConfiguration:
    if token_filename is None:
        token_filename = DEFAULT_TOKEN_FILENAME
    if cert_filename is None:
        cert_filename = DEFAULT_CERT_FILENAME
    if kubernetes_service_host is None:
        kubernetes_service_host = os.environ.get(KUBERNETES_SERVICE_HOST_ENV)
    if kubernetes_service_port is None:
        kubernetes_service_port = os.environ.get(KUBERNETES_SERVICE_PORT_ENV)
    namespace = DEFAULT_NAMESAPCE_FILENAME.read_text().strip()
    return ClientConfiguration(
        url=f"https://{kubernetes_service_host}:{kubernetes_service_port}",
        server_ca_file=cert_filename,
        client_cert_file=None,
        client_key_file=None,
        namespace=namespace,
        token_file=token_filename,
        try_refresh_token=try_refresh_token,
    )
