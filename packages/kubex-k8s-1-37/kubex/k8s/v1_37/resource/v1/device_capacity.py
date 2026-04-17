from kubex.k8s.v1_37.resource.v1.capacity_request_policy import CapacityRequestPolicy
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class DeviceCapacity(BaseK8sModel):
    """DeviceCapacity describes a quantity associated with a device."""

    request_policy: CapacityRequestPolicy | None = Field(
        default=None,
        alias="requestPolicy",
        description="RequestPolicy defines how this DeviceCapacity must be consumed when the device is allowed to be shared by multiple allocations. The Device must have allowMultipleAllocations set to true in order to set a requestPolicy. If unset, capacity requests are unconstrained: requests can consume any amount of capacity, as long as the total consumed across all allocations does not exceed the device's defined capacity. If request is also unset, default is the full capacity value.",
    )
    value: str = Field(
        ...,
        alias="value",
        description="Value defines how much of a certain capacity that device has. This field reflects the fixed total capacity and does not change. The consumed amount is tracked separately by scheduler and does not affect this value.",
    )
