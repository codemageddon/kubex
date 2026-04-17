from kubex.k8s.v1_32.authorization.v1.non_resource_attributes import (
    NonResourceAttributes,
)
from kubex.k8s.v1_32.authorization.v1.resource_attributes import ResourceAttributes
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class SelfSubjectAccessReviewSpec(BaseK8sModel):
    """SelfSubjectAccessReviewSpec is a description of the access request. Exactly one of ResourceAuthorizationAttributes and NonResourceAuthorizationAttributes must be set"""

    non_resource_attributes: NonResourceAttributes | None = Field(
        default=None,
        alias="nonResourceAttributes",
        description="NonResourceAttributes describes information for a non-resource access request",
    )
    resource_attributes: ResourceAttributes | None = Field(
        default=None,
        alias="resourceAttributes",
        description="ResourceAuthorizationAttributes describes information for a resource access request",
    )
