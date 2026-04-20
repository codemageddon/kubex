from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class NodeAllocatableResourceClaimStatus(BaseK8sModel):
    """NodeAllocatableResourceClaimStatus describes the status of node allocatable resources allocated via DRA."""

    containers: list[str] | None = Field(
        default=None,
        alias="containers",
        description="Containers lists the names of all containers in this pod that reference the claim.",
    )
    resource_claim_name: str = Field(
        ...,
        alias="resourceClaimName",
        description="ResourceClaimName is the resource claim referenced by the pod that resulted in this node allocatable resource allocation.",
    )
    resources: dict[str, str] = Field(
        ...,
        alias="resources",
        description="Resources is a map of the node-allocatable resource name to the aggregate quantity allocated to the claim.",
    )
