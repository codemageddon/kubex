from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class LinuxContainerUser(BaseK8sModel):
    """LinuxContainerUser represents user identity information in Linux containers"""

    gid: int = Field(
        ...,
        alias="gid",
        description="gid is the primary gid initially attached to the first process in the container",
    )
    supplemental_groups: list[int] | None = Field(
        default=None,
        alias="supplementalGroups",
        description="supplementalGroups are the supplemental groups initially attached to the first process in the container",
    )
    uid: int = Field(
        ...,
        alias="uid",
        description="uid is the primary uid initially attached to the first process in the container",
    )
