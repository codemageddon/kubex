from pydantic import Field

from kubex.k8s.v1_36.networking.v1.ingress_load_balancer_status import (
    IngressLoadBalancerStatus,
)
from kubex_core.models.base import BaseK8sModel


class IngressStatus(BaseK8sModel):
    """IngressStatus describe the current state of the Ingress."""

    load_balancer: IngressLoadBalancerStatus | None = Field(
        default=None,
        alias="loadBalancer",
        description="loadBalancer contains the current status of the load-balancer.",
    )
