from pydantic import Field

from kubex.k8s.v1_37.meta.v1.condition import Condition
from kubex.k8s.v1_37.scheduling.v1alpha2.pod_group_resource_claim_status import (
    PodGroupResourceClaimStatus,
)
from kubex_core.models.base import BaseK8sModel


class PodGroupStatus(BaseK8sModel):
    """PodGroupStatus represents information about the status of a pod group."""

    conditions: list[Condition] | None = Field(
        default=None,
        alias="conditions",
        description='Conditions represent the latest observations of the PodGroup\'s state. Known condition types: - "PodGroupScheduled": Indicates whether the scheduling requirement has been satisfied. - "DisruptionTarget": Indicates whether the PodGroup is about to be terminated due to disruption such as preemption. Known reasons for the PodGroupScheduled condition: - "Unschedulable": The PodGroup cannot be scheduled due to resource constraints, affinity/anti-affinity rules, or insufficient capacity for the gang. - "SchedulerError": The PodGroup cannot be scheduled due to some internal error that happened during scheduling, for example due to nodeAffinity parsing errors. Known reasons for the DisruptionTarget condition: - "PreemptionByScheduler": The PodGroup was preempted by the scheduler to make room for higher-priority PodGroups or Pods.',
    )
    resource_claim_statuses: list[PodGroupResourceClaimStatus] | None = Field(
        default=None,
        alias="resourceClaimStatuses",
        description="Status of resource claims.",
    )
