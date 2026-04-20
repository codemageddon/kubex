from pydantic import Field

from kubex.k8s.v1_35.networking.v1.ingress_port_status import IngressPortStatus
from kubex_core.models.base import BaseK8sModel


class IngressLoadBalancerIngress(BaseK8sModel):
    """IngressLoadBalancerIngress represents the status of a load-balancer ingress point."""

    hostname: str | None = Field(
        default=None,
        alias="hostname",
        description="hostname is set for load-balancer ingress points that are DNS based.",
    )
    ip: str | None = Field(
        default=None,
        alias="ip",
        description="ip is set for load-balancer ingress points that are IP based.",
    )
    ports: list[IngressPortStatus] | None = Field(
        default=None,
        alias="ports",
        description="ports provides information about the ports exposed by this LoadBalancer.",
    )
