from pydantic import Field

from kubex.k8s.v1_37.authorization.v1.non_resource_attributes import (
    NonResourceAttributes,
)
from kubex.k8s.v1_37.authorization.v1.resource_attributes import ResourceAttributes
from kubex_core.models.base import BaseK8sModel


class SubjectAccessReviewSpec(BaseK8sModel):
    """SubjectAccessReviewSpec is a description of the access request. Exactly one of resourceAttributes and nonResourceAttributes must be set"""

    extra: dict[str, list[str]] | None = Field(
        default=None,
        alias="extra",
        description="extra corresponds to the user.Info.GetExtra() method from the authenticator. Since that is input to the authorizer it needs a reflection here.",
    )
    groups: list[str] | None = Field(
        default=None,
        alias="groups",
        description="groups is the groups you're testing for.",
    )
    non_resource_attributes: NonResourceAttributes | None = Field(
        default=None,
        alias="nonResourceAttributes",
        description="nonResourceAttributes describes information for a non-resource access request",
    )
    resource_attributes: ResourceAttributes | None = Field(
        default=None,
        alias="resourceAttributes",
        description="resourceAttributes describes information for a resource access request",
    )
    uid: str | None = Field(
        default=None,
        alias="uid",
        description="uid information about the requesting user.",
    )
    user: str | None = Field(
        default=None,
        alias="user",
        description='user is the user you\'re testing for. If you specify "User" but not "Groups", then is it interpreted as "What if User were not a member of any groups',
    )
