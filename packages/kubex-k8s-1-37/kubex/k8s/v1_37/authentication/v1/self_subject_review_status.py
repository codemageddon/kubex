from pydantic import Field

from kubex.k8s.v1_37.authentication.v1.user_info import UserInfo
from kubex_core.models.base import BaseK8sModel


class SelfSubjectReviewStatus(BaseK8sModel):
    """SelfSubjectReviewStatus is filled by the kube-apiserver and sent back to a user."""

    user_info: UserInfo | None = Field(
        default=None,
        alias="userInfo",
        description="userInfo is a set of attributes belonging to the user making this request.",
    )
