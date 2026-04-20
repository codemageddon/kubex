from pydantic import Field

from kubex.k8s.v1_36.core.v1.container_extended_resource_request import (
    ContainerExtendedResourceRequest,
)
from kubex_core.models.base import BaseK8sModel


class PodExtendedResourceClaimStatus(BaseK8sModel):
    """PodExtendedResourceClaimStatus is stored in the PodStatus for the extended resource requests backed by DRA. It stores the generated name for the corresponding special ResourceClaim created by the scheduler."""

    request_mappings: list[ContainerExtendedResourceRequest] = Field(
        ...,
        alias="requestMappings",
        description="RequestMappings identifies the mapping of <container, extended resource backed by DRA> to device request in the generated ResourceClaim.",
    )
    resource_claim_name: str = Field(
        ...,
        alias="resourceClaimName",
        description="ResourceClaimName is the name of the ResourceClaim that was generated for the Pod in the namespace of the Pod.",
    )
