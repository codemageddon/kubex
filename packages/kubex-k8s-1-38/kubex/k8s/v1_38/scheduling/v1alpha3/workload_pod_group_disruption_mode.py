from pydantic import Field

from kubex.k8s.v1_38.scheduling.v1alpha3.workload_pod_group_all_disruption_mode import (
    WorkloadPodGroupAllDisruptionMode,
)
from kubex.k8s.v1_38.scheduling.v1alpha3.workload_pod_group_single_disruption_mode import (
    WorkloadPodGroupSingleDisruptionMode,
)
from kubex_core.models.base import BaseK8sModel


class WorkloadPodGroupDisruptionMode(BaseK8sModel):
    """WorkloadPodGroupDisruptionMode defines how individual pods within a group can be disrupted. Exactly one mode must be set."""

    all: WorkloadPodGroupAllDisruptionMode | None = Field(
        default=None,
        alias="all",
        description="all specifies that all pods in the group must be disrupted together.",
    )
    single: WorkloadPodGroupSingleDisruptionMode | None = Field(
        default=None,
        alias="single",
        description="single specifies that pods can be disrupted independently from each other.",
    )
