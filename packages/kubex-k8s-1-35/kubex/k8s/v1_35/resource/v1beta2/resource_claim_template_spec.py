from pydantic import Field

from kubex.k8s.v1_35.resource.v1beta2.resource_claim_spec import ResourceClaimSpec
from kubex_core.models.base import BaseK8sModel
from kubex_core.models.metadata import ObjectMetadata


class ResourceClaimTemplateSpec(BaseK8sModel):
    """ResourceClaimTemplateSpec contains the metadata and fields for a ResourceClaim."""

    metadata: ObjectMetadata | None = Field(
        default=None,
        alias="metadata",
        description="ObjectMeta may contain labels and annotations that will be copied into the ResourceClaim when creating it. No other fields are allowed and will be rejected during validation.",
    )
    spec: ResourceClaimSpec = Field(
        ...,
        alias="spec",
        description="Spec for the ResourceClaim. The entire content is copied unchanged into the ResourceClaim that gets created from this template. The same fields as in a ResourceClaim are also valid here.",
    )
