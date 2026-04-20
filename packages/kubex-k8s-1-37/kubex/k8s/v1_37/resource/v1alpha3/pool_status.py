from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class PoolStatus(BaseK8sModel):
    """PoolStatus contains status information for a single resource pool."""

    allocated_devices: int | None = Field(
        default=None,
        alias="allocatedDevices",
        description="AllocatedDevices is the number of devices currently allocated to claims. A value of 0 means no devices are allocated. May be unset when validationError is set.",
    )
    available_devices: int | None = Field(
        default=None,
        alias="availableDevices",
        description="AvailableDevices is the number of devices available for allocation. This equals TotalDevices - AllocatedDevices - UnavailableDevices. A value of 0 means no devices are currently available. May be unset when validationError is set.",
    )
    driver: str = Field(
        ...,
        alias="driver",
        description='Driver is the DRA driver name for this pool. Must be a DNS subdomain (e.g., "gpu.example.com").',
    )
    generation: int = Field(
        ...,
        alias="generation",
        description="Generation is the pool generation observed across all ResourceSlices in this pool. Only the latest generation is reported. During a generation rollout, if not all slices at the latest generation have been published, the pool is included with a validationError and device counts unset.",
    )
    node_name: str | None = Field(
        default=None,
        alias="nodeName",
        description="NodeName is the node this pool is associated with. When omitted, the pool is not associated with a specific node. Must be a valid DNS subdomain name (RFC1123).",
    )
    pool_name: str = Field(
        ...,
        alias="poolName",
        description='PoolName is the name of the pool. Must be a valid resource pool name (DNS subdomains separated by "/").',
    )
    resource_slice_count: int | None = Field(
        default=None,
        alias="resourceSliceCount",
        description="ResourceSliceCount is the number of ResourceSlices that make up this pool. May be unset when validationError is set.",
    )
    total_devices: int | None = Field(
        default=None,
        alias="totalDevices",
        description="TotalDevices is the total number of devices in the pool across all slices. A value of 0 means the pool has no devices. May be unset when validationError is set.",
    )
    unavailable_devices: int | None = Field(
        default=None,
        alias="unavailableDevices",
        description="UnavailableDevices is the number of devices that are not available due to taints or other conditions, but are not allocated. A value of 0 means all unallocated devices are available. May be unset when validationError is set.",
    )
    validation_error: str | None = Field(
        default=None,
        alias="validationError",
        description="ValidationError is set when the pool's data could not be fully validated (e.g., incomplete slice publication). When set, device count fields and ResourceSliceCount may be unset.",
    )
