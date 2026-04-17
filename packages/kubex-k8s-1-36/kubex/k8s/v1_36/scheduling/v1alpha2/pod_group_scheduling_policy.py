from kubex.k8s.v1_36.scheduling.v1alpha2.basic_scheduling_policy import (
    BasicSchedulingPolicy,
)
from kubex.k8s.v1_36.scheduling.v1alpha2.gang_scheduling_policy import (
    GangSchedulingPolicy,
)
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class PodGroupSchedulingPolicy(BaseK8sModel):
    """PodGroupSchedulingPolicy defines the scheduling configuration for a PodGroup. Exactly one policy must be set."""

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
