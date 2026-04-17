from kubex.k8s.v1_36.core.v1.load_balancer_status import LoadBalancerStatus
from kubex.k8s.v1_36.meta.v1.condition import Condition
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class ServiceStatus(BaseK8sModel):
    """ServiceStatus represents the current status of a service."""

    conditions: list[Condition] | None = Field(
        default=None, alias="conditions", description="Current service state"
    )
    load_balancer: LoadBalancerStatus | None = Field(
        default=None,
        alias="loadBalancer",
        description="LoadBalancer contains the current status of the load-balancer, if one is present.",
    )
