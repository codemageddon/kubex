from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class ResourceClaimConsumerReference(BaseK8sModel):
    """ResourceClaimConsumerReference contains enough information to let you locate the consumer of a ResourceClaim. The user must be a resource in the same namespace as the ResourceClaim."""

    api_group: str | None = Field(
        default=None,
        alias="apiGroup",
        description="APIGroup is the group for the resource being referenced. It is empty for the core API. This matches the group in the APIVersion that is used when creating the resources.",
    )
    name: str = Field(
        ..., alias="name", description="Name is the name of resource being referenced."
    )
    resource: str = Field(
        ...,
        alias="resource",
        description='Resource is the type of resource being referenced, for example "pods".',
    )
    uid: str = Field(
        ...,
        alias="uid",
        description="UID identifies exactly one incarnation of the resource.",
    )
