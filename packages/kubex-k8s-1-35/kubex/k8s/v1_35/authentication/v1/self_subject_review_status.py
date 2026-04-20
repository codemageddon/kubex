from pydantic import Field

from kubex.k8s.v1_35.authentication.v1.user_info import UserInfo
from kubex_core.models.base import BaseK8sModel


class SelfSubjectReviewStatus(BaseK8sModel):
    """SelfSubjectReviewStatus is filled by the kube-apiserver and sent back to a user."""

    user_info: UserInfo | None = Field(
        default=None,
        alias="userInfo",
        description="User attributes of the user making this request.",
    )
