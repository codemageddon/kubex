import pathlib

import httpx

_CURRENT_PATH = pathlib.Path(__file__)
_CERTS_PATH = _CURRENT_PATH.parent.parent.parent.parent / "scratches" / ".certs"
_BASE_URL = "https://127.0.0.1:6443"
_CERT = (
    str(_CERTS_PATH / "client.crt"),
    str(_CERTS_PATH / "client.key"),
)
_VERIFY = str(_CERTS_PATH / "server_ca.crt")
CLIENT_PARAMS = {
    "base_url": _BASE_URL,
    "cert": _CERT,
    "verify": _VERIFY,
}


def get_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=_BASE_URL, cert=_CERT, verify=_VERIFY)
