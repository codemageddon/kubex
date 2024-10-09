import pathlib
from base64 import b64decode

from kubex.json import json

SERVICE_HOST_ENV_NAME = "KUBERNETES_SERVICE_HOST"
SERVICE_PORT_ENV_NAME = "KUBERNETES_SERVICE_PORT"
SERVICE_TOKEN_FILENAME = pathlib.Path(
    "/var/run/secrets/kubernetes.io/serviceaccount/token"
)
SERVICE_CERT_FILENAME = pathlib.Path(
    "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"
)


def load_incluster_config():
    token = read_token(SERVICE_TOKEN_FILENAME)
    exp = get_token_expiration(token)

    pass
    # if (SERVICE_HOST_ENV_NAME not in os.environ or
    #         SERVICE_PORT_ENV_NAME not in os.environ):
    #     raise ConfigException("Service host/port is not set.")
    #
    # if (not os.environ[SERVICE_HOST_ENV_NAME] or
    #         not os.environ[SERVICE_PORT_ENV_NAME]):
    #     raise ConfigException("Service host/port is set but empty.")
    #
    # host = (
    #     "https://" + _join_host_port(os.environ[SERVICE_HOST_ENV_NAME],
    #                                  os.environ[SERVICE_PORT_ENV_NAME]))
    #
    # token = open(SERVICE_TOKEN_FILENAME).read().strip()
    #
    # configuration = Configuration()
    # configuration.host = host
    # configuration.verify_ssl = False
    # configuration.debug = False
    # configuration.ssl_ca_cert = SERVICE_CERT_FILENAME
    # configuration.api_key = {"authorization": token}
    # Configuration.set_default(configuration)


def get_token_expiration(token: str) -> int | float | None:
    _, body, _ = token.split(".")
    decoded_body = b64decode(body)
    deserializde_body = json.loads(decoded_body)
    return deserializde_body.get("exp")


def read_token(token_file: pathlib.Path) -> str:
    content = token_file.read_text()
    return content
