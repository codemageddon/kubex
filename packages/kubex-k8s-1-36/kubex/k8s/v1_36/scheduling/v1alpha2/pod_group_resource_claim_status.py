from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class PodGroupResourceClaimStatus(BaseK8sModel):
    """PodGroupResourceClaimStatus is stored in the PodGroupStatus for each PodGroupResourceClaim which references a ResourceClaimTemplate. It stores the generated name for the corresponding ResourceClaim."""

    name: str = Field(
        ...,
        alias="name",
        description="Name uniquely identifies this resource claim inside the PodGroup. This must match the name of an entry in podgroup.spec.resourceClaims, which implies that the string must be a DNS_LABEL.",
    )
    resource_claim_name: str | None = Field(
        default=None,
        alias="resourceClaimName",
        description="ResourceClaimName is the name of the ResourceClaim that was generated for the PodGroup in the namespace of the PodGroup. If this is unset, then generating a ResourceClaim was not necessary. The podgroup.spec.resourceClaims entry can be ignored in this case.",
    )
