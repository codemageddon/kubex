import datetime

from pydantic import Field

from kubex.k8s.v1_35.core.v1.node_selector import NodeSelector
from kubex.k8s.v1_35.resource.v1beta2.device_allocation_result import (
    DeviceAllocationResult,
)
from kubex_core.models.base import BaseK8sModel


class AllocationResult(BaseK8sModel):
    """AllocationResult contains attributes of an allocated resource."""

    allocation_timestamp: datetime.datetime | None = Field(
        default=None,
        alias="allocationTimestamp",
        description="AllocationTimestamp stores the time when the resources were allocated. This field is not guaranteed to be set, in which case that time is unknown. This is an alpha field and requires enabling the DRADeviceBindingConditions and DRAResourceClaimDeviceStatus feature gate.",
    )
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
