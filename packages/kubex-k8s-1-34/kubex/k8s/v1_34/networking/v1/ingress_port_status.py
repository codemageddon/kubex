from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class IngressPortStatus(BaseK8sModel):
    """IngressPortStatus represents the error condition of a service port"""

    error: str | None = Field(
        default=None,
        alias="error",
        description="error is to record the problem with the service port The format of the error shall comply with the following rules: - built-in error values shall be specified in this file and those shall use CamelCase names - cloud provider specific error values must have names that comply with the format foo.example.com/CamelCase.",
    )
    port: int = Field(
        ..., alias="port", description="port is the port number of the ingress port."
    )
    protocol: str = Field(
        ...,
        alias="protocol",
        description='protocol is the protocol of the ingress port. The supported values are: "TCP", "UDP", "SCTP"',
    )
