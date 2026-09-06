import datetime

from pydantic import Field

from kubex.k8s.v1_38.core.v1.volume_health_condition import VolumeHealthCondition
from kubex_core.models.base import BaseK8sModel


class PodVolumeHealth(BaseK8sModel):
    """PodVolumeHealth contains health information for a volume used by a pod, reported by the CSI node plugin via the kubelet."""

    health_conditions: list[VolumeHealthCondition] | None = Field(
        default=None,
        alias="healthConditions",
        description="conditions is the set of adverse conditions reported by the CSI node plugin for this volume on this node. At most 16 conditions may be reported.",
    )
    last_transition_time: datetime.datetime | None = Field(
        default=None,
        alias="lastTransitionTime",
        description="lastTransitionTime is when the current set of conditions first appeared.",
    )
    name: str = Field(
        ..., alias="name", description="name matches an entry in pod.spec.volumes."
    )
