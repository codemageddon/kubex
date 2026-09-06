from pydantic import Field

from kubex.k8s.v1_37.core.v1.node_allocatable_mapped_resources import (
    NodeAllocatableMappedResources,
)
from kubex.k8s.v1_37.core.v1.node_allocatable_overhead_resources import (
    NodeAllocatableOverheadResources,
)
from kubex_core.models.base import BaseK8sModel


class NodeAllocatableResourceClaimStatus(BaseK8sModel):
    """NodeAllocatableResourceClaimStatus describes the status of node allocatable resources allocated via DRA."""

    containers: list[str] | None = Field(
        default=None,
        alias="containers",
        description="Containers lists the names of all containers in this pod that reference the claim.",
    )
    mapping: list[NodeAllocatableMappedResources] | None = Field(
        default=None,
        alias="mapping",
        description="Mapping contains allocations through devices mapped in the device spec's `nodeAllocatableResources[...].mapping` field. This is used by kubelet for pod level and container-level cgroup enforcement.",
    )
    overhead: list[NodeAllocatableOverheadResources] | None = Field(
        default=None,
        alias="overhead",
        description="Overhead contains allocations through devices mapped in the device spec's `nodeAllocatableResources[...].overhead` field. This is used by kubelet for pod level and container-level cgroup enforcement.",
    )
    resource_claim_name: str = Field(
        ...,
        alias="resourceClaimName",
        description="ResourceClaimName is the resource claim referenced by the pod that resulted in this node allocatable resource allocation.",
    )
