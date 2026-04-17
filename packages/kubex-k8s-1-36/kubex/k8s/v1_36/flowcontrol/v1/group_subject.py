from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class GroupSubject(BaseK8sModel):
    """GroupSubject holds detailed information for group-kind subject."""

    name: str = Field(
        ...,
        alias="name",
        description='name is the user group that matches, or "*" to match all user groups. See https://github.com/kubernetes/apiserver/blob/master/pkg/authentication/user/user.go for some well-known group names. Required.',
    )
