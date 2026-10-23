from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class ContainerPort(BaseK8sModel):
    """ContainerPort represents a network port in a single container."""

    container_port: int = Field(
        ...,
        alias="containerPort",
        description="containerPort is the number of port to expose on the pod's IP address. This must be a valid port number, 0 < x < 65536.",
    )
    host_ip: str | None = Field(
        default=None,
        alias="hostIP",
        description="hostIP is the host IP to bind the external port to.",
    )
    host_port: int | None = Field(
        default=None,
        alias="hostPort",
        description="hostPort is the number of port to expose on the host. If specified, this must be a valid port number, 0 < x < 65536. If HostNetwork is specified, this must match ContainerPort. Most containers do not need this.",
    )
    name: str | None = Field(
        default=None,
        alias="name",
        description="name is the name of the port. If specified, this must be an IANA_SVC_NAME and unique within the pod. Each named port in a pod must have a unique name. Name for the port that can be referred to by services.",
    )
    protocol: str | None = Field(
        default=None,
        alias="protocol",
        description='protocol is the protocol for port. Must be UDP, TCP, or SCTP. Defaults to "TCP".',
    )
