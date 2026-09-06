from pydantic import Field

from kubex.k8s.v1_38.resource.v1alpha3.shareable_capacity_status import (
    ShareableCapacityStatus,
)
from kubex_core.models.base import BaseK8sModel


class ShareableSummaryStatus(BaseK8sModel):
    """ShareableSummaryStatus reports aggregate capacity for a pool that contains devices with AllowMultipleAllocations."""

    capacity: list[ShareableCapacityStatus] | None = Field(
        default=None,
        alias="capacity",
        description="Capacity reports aggregate total, consumed, and available amounts per shareable capacity key across the pool.",
    )
    fully_available_devices: int = Field(
        ...,
        alias="fullyAvailableDevices",
        description="FullyAvailableDevices is the number of shareable devices with no capacity consumed.",
    )
    partially_available_devices: int = Field(
        ...,
        alias="partiallyAvailableDevices",
        description="PartiallyAvailableDevices is the number of shareable devices with some but not all capacity consumed.",
    )
