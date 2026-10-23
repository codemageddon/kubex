from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class SELinuxOptions(BaseK8sModel):
    """SELinuxOptions are the labels to be applied to the container"""

    level: str | None = Field(
        default=None,
        alias="level",
        description="level is SELinux level label that applies to the container.",
    )
    role: str | None = Field(
        default=None,
        alias="role",
        description="role is a SELinux role label that applies to the container.",
    )
    type_: str | None = Field(
        default=None,
        alias="type",
        description="type is a SELinux type label that applies to the container.",
    )
    user: str | None = Field(
        default=None,
        alias="user",
        description="user is a SELinux user label that applies to the container.",
    )
