from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class NodeFeatures(BaseK8sModel):
    """NodeFeatures describes the set of features implemented by the CRI implementation. The features contained in the NodeFeatures should depend only on the cri implementation independent of runtime handlers."""

    supplemental_groups_policy: bool | None = Field(
        default=None,
        alias="supplementalGroupsPolicy",
        description="SupplementalGroupsPolicy is set to true if the runtime supports SupplementalGroupsPolicy and ContainerUser.",
    )
