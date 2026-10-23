import datetime

from pydantic import Field

from kubex.k8s.v1_37.core.v1.volume_health_condition import VolumeHealthCondition
from kubex_core.models.base import BaseK8sModel


class VolumeHealthStatus(BaseK8sModel):
    """VolumeHealthStatus contains health information for a volume reported by the CSI controller plugin."""

    health_conditions: list[VolumeHealthCondition] | None = Field(
        default=None,
        alias="healthConditions",
        description="conditions is the set of adverse conditions reported by the CSI controller plugin. An empty list means no adverse condition. At most 16 conditions may be reported.",
    )
    last_transition_time: datetime.datetime | None = Field(
        default=None,
        alias="lastTransitionTime",
        description="lastTransitionTime is when the current set of conditions first appeared.",
    )
