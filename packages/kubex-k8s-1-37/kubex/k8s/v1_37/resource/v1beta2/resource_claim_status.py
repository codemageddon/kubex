from kubex.k8s.v1_37.resource.v1beta2.allocated_device_status import (
    AllocatedDeviceStatus,
)
from kubex.k8s.v1_37.resource.v1beta2.allocation_result import AllocationResult
from kubex.k8s.v1_37.resource.v1beta2.resource_claim_consumer_reference import (
    ResourceClaimConsumerReference,
)
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class ResourceClaimStatus(BaseK8sModel):
    """ResourceClaimStatus tracks whether the resource has been allocated and what the result of that was."""

    allocation: AllocationResult | None = Field(
        default=None,
        alias="allocation",
        description="Allocation is set once the claim has been allocated successfully.",
    )
    devices: list[AllocatedDeviceStatus] | None = Field(
        default=None,
        alias="devices",
        description="Devices contains the status of each device allocated for this claim, as reported by the driver. This can include driver-specific information. Entries are owned by their respective drivers.",
    )
    reserved_for: list[ResourceClaimConsumerReference] | None = Field(
        default=None,
        alias="reservedFor",
        description="ReservedFor indicates which entities are currently allowed to use the claim. A Pod which references a ResourceClaim which is not reserved for that Pod will not be started. A claim that is in use or might be in use because it has been reserved must not get deallocated. In a cluster with multiple scheduler instances, two pods might get scheduled concurrently by different schedulers. When they reference the same ResourceClaim which already has reached its maximum number of consumers, only one pod can be scheduled. Both schedulers try to add their pod to the claim.status.reservedFor field, but only the update that reaches the API server first gets stored. The other one fails with an error and the scheduler which issued it knows that it must put the pod back into the queue, waiting for the ResourceClaim to become usable again. There can be at most 256 such reservations. This may get increased in the future, but not reduced.",
    )
