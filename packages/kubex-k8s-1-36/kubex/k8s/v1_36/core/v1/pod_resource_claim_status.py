from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class PodResourceClaimStatus(BaseK8sModel):
    """PodResourceClaimStatus is stored in the PodStatus for each PodResourceClaim which references a ResourceClaimTemplate. It stores the generated name for the corresponding ResourceClaim."""

    name: str = Field(
        ...,
        alias="name",
        description="Name uniquely identifies this resource claim inside the pod. This must match the name of an entry in pod.spec.resourceClaims, which implies that the string must be a DNS_LABEL.",
    )
    resource_claim_name: str | None = Field(
        default=None,
        alias="resourceClaimName",
        description="ResourceClaimName is the name of the ResourceClaim that was generated for the Pod in the namespace of the Pod. When the DRAWorkloadResourceClaims feature is enabled and the corresponding PodResourceClaim matches a PodGroupResourceClaim made by the Pod's PodGroup, then this is the name of the ResourceClaim generated and reserved for the PodGroup. If this is unset, then generating a ResourceClaim was not necessary. The pod.spec.resourceClaims entry can be ignored in this case.",
    )
