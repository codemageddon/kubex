from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class TCPSocketAction(BaseK8sModel):
    """TCPSocketAction describes an action based on opening a socket"""

    host: str | None = Field(
        default=None,
        alias="host",
        description="host is the optional host name to connect to, defaults to the pod IP.",
    )
    port: int | str = Field(
        ...,
        alias="port",
        description="port is the number or name of the port to access on the container. Number must be in the range 1 to 65535. Name must be an IANA_SVC_NAME.",
    )
