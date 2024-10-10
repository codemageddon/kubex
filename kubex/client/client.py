import pathlib

import httpx

# Following constants are just for development purposes and should be removed after configuration reading is implemented
_CURRENT_PATH = pathlib.Path(__file__)
_CERTS_PATH = _CURRENT_PATH.parent.parent.parent / "scratches" / ".certs"

_DEFAULT_BASE_URL = "https://127.0.0.1:6443"
_DEFAULT_SERVER_CA = str(_CERTS_PATH / "server_ca.crt")
_DEFAULT_CLIENT_CERT = str(_CERTS_PATH / "client.crt")
_DEFAULT_CLIENT_KEY = str(_CERTS_PATH / "client.key")


class ClientConfiguration:
    def __init__(
        self,
        url: str | None = None,
        server_ca_file: str | None = None,
        client_cert_file: str | None = None,
        client_key_file: str | None = None,
        namespace: str | None = None,
    ) -> None:
        self.base_url = url or _DEFAULT_BASE_URL
        self.server_ca_file = server_ca_file or _DEFAULT_SERVER_CA
        self.client_cert_file = client_cert_file or _DEFAULT_CLIENT_CERT
        self.client_key_file = client_key_file or _DEFAULT_CLIENT_KEY
        self.namespace = namespace or "default"


class Client:
    def __init__(self, configuration: ClientConfiguration | None = None) -> None:
        self.configuration = configuration or ClientConfiguration()

    def get_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.configuration.base_url,
            cert=(
                self.configuration.client_cert_file,
                self.configuration.client_key_file,
            ),
            verify=self.configuration.server_ca_file,
        )
