from kubex.k8s.v1_33.meta.v1.condition import Condition
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class ServiceCIDRStatus(BaseK8sModel):
    """ServiceCIDRStatus describes the current state of the ServiceCIDR."""

    conditions: list[Condition] | None = Field(
        default=None,
        alias="conditions",
        description="conditions holds an array of metav1.Condition that describe the state of the ServiceCIDR. Current service state",
    )
