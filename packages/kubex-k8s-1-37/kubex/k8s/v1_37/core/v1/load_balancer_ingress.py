from pydantic import Field

from kubex.k8s.v1_37.core.v1.port_status import PortStatus
from kubex_core.models.base import BaseK8sModel


class LoadBalancerIngress(BaseK8sModel):
    """LoadBalancerIngress represents the status of a load-balancer ingress point: traffic intended for the service should be sent to an ingress point."""

    hostname: str | None = Field(
        default=None,
        alias="hostname",
        description="Hostname is set for load-balancer ingress points that are DNS based (typically AWS load-balancers)",
    )
    ip: str | None = Field(
        default=None,
        alias="ip",
        description="IP is set for load-balancer ingress points that are IP based (typically GCE or OpenStack load-balancers)",
    )
    ip_mode: str | None = Field(
        default=None,
        alias="ipMode",
        description='IPMode specifies how the load-balancer IP behaves, and may only be specified when the ip field is specified. Setting this to "VIP" indicates that traffic is delivered to the node with the destination set to the load-balancer\'s IP and port. Setting this to "Proxy" indicates that traffic is delivered to the node or pod with the destination set to the node\'s IP and node port or the pod\'s IP and port. Service implementations may use this information to adjust traffic routing.',
    )
    ports: list[PortStatus] | None = Field(
        default=None,
        alias="ports",
        description="Ports is a list of records of service ports If used, every port defined in the service should have an entry in it",
    )
