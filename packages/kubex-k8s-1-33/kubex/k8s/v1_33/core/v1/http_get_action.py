from pydantic import Field

from kubex.k8s.v1_33.core.v1.http_header import HTTPHeader
from kubex_core.models.base import BaseK8sModel


class HTTPGetAction(BaseK8sModel):
    """HTTPGetAction describes an action based on HTTP Get requests."""

    host: str | None = Field(
        default=None,
        alias="host",
        description='Host name to connect to, defaults to the pod IP. You probably want to set "Host" in httpHeaders instead.',
    )
    http_headers: list[HTTPHeader] | None = Field(
        default=None,
        alias="httpHeaders",
        description="Custom headers to set in the request. HTTP allows repeated headers.",
    )
    path: str | None = Field(
        default=None, alias="path", description="Path to access on the HTTP server."
    )
    port: int | str = Field(
        ...,
        alias="port",
        description="Name or number of the port to access on the container. Number must be in the range 1 to 65535. Name must be an IANA_SVC_NAME.",
    )
    scheme: str | None = Field(
        default=None,
        alias="scheme",
        description="Scheme to use for connecting to the host. Defaults to HTTP.",
    )
