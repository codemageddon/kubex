from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class UserInfo(BaseK8sModel):
    """UserInfo holds the information about the user needed to implement the user.Info interface."""

    extra: dict[str, list[str]] | None = Field(
        default=None,
        alias="extra",
        description="Any additional information provided by the authenticator.",
    )
    groups: list[str] | None = Field(
        default=None,
        alias="groups",
        description="The names of groups this user is a part of.",
    )
    uid: str | None = Field(
        default=None,
        alias="uid",
        description="A unique value that identifies this user across time. If this user is deleted and another user by the same name is added, they will have different UIDs.",
    )
    username: str | None = Field(
        default=None,
        alias="username",
        description="The name that uniquely identifies this user among all active users.",
    )
