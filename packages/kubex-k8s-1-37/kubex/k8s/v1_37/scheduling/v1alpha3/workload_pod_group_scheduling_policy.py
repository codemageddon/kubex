from pydantic import Field

from kubex.k8s.v1_37.scheduling.v1alpha3.workload_pod_group_basic_scheduling_policy import (
    WorkloadPodGroupBasicSchedulingPolicy,
)
from kubex.k8s.v1_37.scheduling.v1alpha3.workload_pod_group_gang_scheduling_policy import (
    WorkloadPodGroupGangSchedulingPolicy,
)
from kubex_core.models.base import BaseK8sModel


class WorkloadPodGroupSchedulingPolicy(BaseK8sModel):
    """WorkloadPodGroupSchedulingPolicy defines the scheduling policy for a group of pods managed by a workload controller. Exactly one policy must be set."""

    basic: WorkloadPodGroupBasicSchedulingPolicy | None = Field(
        default=None,
        alias="basic",
        description="basic specifies that standard, pod-by-pod Kubernetes scheduling behavior should be used.",
    )
    gang: WorkloadPodGroupGangSchedulingPolicy | None = Field(
        default=None,
        alias="gang",
        description="gang specifies all-or-nothing scheduling semantics.",
    )
