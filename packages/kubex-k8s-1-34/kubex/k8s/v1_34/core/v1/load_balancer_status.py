from kubex.k8s.v1_34.core.v1.load_balancer_ingress import LoadBalancerIngress
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class LoadBalancerStatus(BaseK8sModel):
    """LoadBalancerStatus represents the status of a load-balancer."""

    ingress: list[LoadBalancerIngress] | None = Field(
        default=None,
        alias="ingress",
        description="Ingress is a list containing ingress points for the load-balancer. Traffic intended for the service should be sent to these ingress points.",
    )
