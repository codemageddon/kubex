from pydantic import Field

from kubex.k8s.v1_33.core.v1.resource_claim import ResourceClaim
from kubex_core.models.base import BaseK8sModel


class ResourceRequirements(BaseK8sModel):
    """ResourceRequirements describes the compute resource requirements."""

    claims: list[ResourceClaim] | None = Field(
        default=None,
        alias="claims",
        description="Claims lists the names of resources, defined in spec.resourceClaims, that are used by this container. This is an alpha field and requires enabling the DynamicResourceAllocation feature gate. This field is immutable. It can only be set for containers.",
    )
    limits: dict[str, str] | None = Field(
        default=None,
        alias="limits",
        description="Limits describes the maximum amount of compute resources allowed. More info: https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/",
    )
    requests: dict[str, str] | None = Field(
        default=None,
        alias="requests",
        description="Requests describes the minimum amount of compute resources required. If Requests is omitted for a container, it defaults to Limits if that is explicitly specified, otherwise to an implementation-defined value. Requests cannot exceed Limits. More info: https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/",
    )
