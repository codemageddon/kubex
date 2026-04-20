from pydantic import Field

from kubex.k8s.v1_37.resource.v1.device_allocation_configuration import (
    DeviceAllocationConfiguration,
)
from kubex.k8s.v1_37.resource.v1.device_request_allocation_result import (
    DeviceRequestAllocationResult,
)
from kubex_core.models.base import BaseK8sModel


class DeviceAllocationResult(BaseK8sModel):
    """DeviceAllocationResult is the result of allocating devices."""

    config: list[DeviceAllocationConfiguration] | None = Field(
        default=None,
        alias="config",
        description="This field is a combination of all the claim and class configuration parameters. Drivers can distinguish between those based on a flag. This includes configuration parameters for drivers which have no allocated devices in the result because it is up to the drivers which configuration parameters they support. They can silently ignore unknown configuration parameters.",
    )
    results: list[DeviceRequestAllocationResult] | None = Field(
        default=None,
        alias="results",
        description="Results lists all allocated devices.",
    )
