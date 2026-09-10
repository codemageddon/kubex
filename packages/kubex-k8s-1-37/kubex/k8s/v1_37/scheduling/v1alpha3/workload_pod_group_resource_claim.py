from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class WorkloadPodGroupResourceClaim(BaseK8sModel):
    """WorkloadPodGroupResourceClaim references a dynamic resource claim that is shared across pods in the group."""

    name: str = Field(
        ...,
        alias="name",
        description="name uniquely identifies this resource claim inside the group. This field is required. It must be a DNS_LABEL.",
    )
    resource_claim_name: str | None = Field(
        default=None,
        alias="resourceClaimName",
        description="resourceClaimName is the name of a ResourceClaim object in the same namespace. This field is optional. If it is not specified, no resource claim is used. If set, it must be a DNS subdomain.",
    )
    resource_claim_template_name: str | None = Field(
        default=None,
        alias="resourceClaimTemplateName",
        description="resourceClaimTemplateName is the name of a ResourceClaimTemplate object in the same namespace. This field is optional. If it is not specified, no resource claim template is used. If set, it must be a DNS subdomain.",
    )
