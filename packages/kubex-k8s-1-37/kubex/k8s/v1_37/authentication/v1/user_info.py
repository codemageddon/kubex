from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class UserInfo(BaseK8sModel):
    """UserInfo holds the information about the user needed to implement the user.Info interface."""

    extra: dict[str, list[str]] | None = Field(
        default=None,
        alias="extra",
        description="extra is any additional information provided by the authenticator.",
    )
    groups: list[str] | None = Field(
        default=None,
        alias="groups",
        description="groups is the names of groups this user is a part of.",
    )
    uid: str | None = Field(
        default=None,
        alias="uid",
        description="uid is a unique value that identifies this user across time. If this user is deleted and another user by the same name is added, they will have different UIDs.",
    )
    username: str | None = Field(
        default=None,
        alias="username",
        description="username is the name that uniquely identifies this user among all active users.",
    )
