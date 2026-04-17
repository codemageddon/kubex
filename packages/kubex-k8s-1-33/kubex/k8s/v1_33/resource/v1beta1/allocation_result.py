from kubex.k8s.v1_33.core.v1.node_selector import NodeSelector
from kubex.k8s.v1_33.resource.v1beta1.device_allocation_result import (
    DeviceAllocationResult,
)
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class AllocationResult(BaseK8sModel):
    """AllocationResult contains attributes of an allocated resource."""

    devices: DeviceAllocationResult | None = Field(
        default=None,
        alias="devices",
        description="Devices is the result of allocating devices.",
    )
    node_selector: NodeSelector | None = Field(
        default=None,
        alias="nodeSelector",
        description="NodeSelector defines where the allocated resources are available. If unset, they are available everywhere.",
    )
