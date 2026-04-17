from kubex.k8s.v1_32.resource.v1beta1.opaque_device_configuration import (
    OpaqueDeviceConfiguration,
)
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class DeviceAllocationConfiguration(BaseK8sModel):
    """DeviceAllocationConfiguration gets embedded in an AllocationResult."""

    opaque: OpaqueDeviceConfiguration | None = Field(
        default=None,
        alias="opaque",
        description="Opaque provides driver-specific configuration parameters.",
    )
    requests: list[str] | None = Field(
        default=None,
        alias="requests",
        description="Requests lists the names of requests where the configuration applies. If empty, its applies to all requests.",
    )
    source: str = Field(
        ...,
        alias="source",
        description="Source records whether the configuration comes from a class and thus is not something that a normal user would have been able to set or from a claim.",
    )
