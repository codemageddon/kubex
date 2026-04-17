from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class PortStatus(BaseK8sModel):
    """PortStatus represents the error condition of a service port"""

    error: str | None = Field(
        default=None,
        alias="error",
        description="Error is to record the problem with the service port The format of the error shall comply with the following rules: - built-in error values shall be specified in this file and those shall use CamelCase names - cloud provider specific error values must have names that comply with the format foo.example.com/CamelCase.",
    )
    port: int = Field(
        ...,
        alias="port",
        description="Port is the port number of the service port of which status is recorded here",
    )
    protocol: str = Field(
        ...,
        alias="protocol",
        description='Protocol is the protocol of the service port of which status is recorded here The supported values are: "TCP", "UDP", "SCTP"',
    )
