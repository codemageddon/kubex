from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class ResourceClaim(BaseK8sModel):
    """ResourceClaim references one entry in PodSpec.ResourceClaims."""

    name: str = Field(
        ...,
        alias="name",
        description="Name must match the name of one entry in pod.spec.resourceClaims of the Pod where this field is used. It makes that resource available inside a container.",
    )
    request: str | None = Field(
        default=None,
        alias="request",
        description="Request is the name chosen for a request in the referenced claim. If empty, everything from the claim is made available, otherwise only the result of this request.",
    )
