from pydantic import Field

from kubex.k8s.v1_37.networking.v1.ingress_load_balancer_ingress import (
    IngressLoadBalancerIngress,
)
from kubex_core.models.base import BaseK8sModel


class IngressLoadBalancerStatus(BaseK8sModel):
    """IngressLoadBalancerStatus represents the status of a load-balancer."""

    ingress: list[IngressLoadBalancerIngress] | None = Field(
        default=None,
        alias="ingress",
        description="ingress is a list containing ingress points for the load-balancer.",
    )
