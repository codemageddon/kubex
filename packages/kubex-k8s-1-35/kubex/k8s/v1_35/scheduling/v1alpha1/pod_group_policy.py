from kubex.k8s.v1_35.scheduling.v1alpha1.basic_scheduling_policy import (
    BasicSchedulingPolicy,
)
from kubex.k8s.v1_35.scheduling.v1alpha1.gang_scheduling_policy import (
    GangSchedulingPolicy,
)
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class PodGroupPolicy(BaseK8sModel):
    """PodGroupPolicy defines the scheduling configuration for a PodGroup."""

    basic: BasicSchedulingPolicy | None = Field(
        default=None,
        alias="basic",
        description="Basic specifies that the pods in this group should be scheduled using standard Kubernetes scheduling behavior.",
    )
    gang: GangSchedulingPolicy | None = Field(
        default=None,
        alias="gang",
        description="Gang specifies that the pods in this group should be scheduled using all-or-nothing semantics.",
    )
