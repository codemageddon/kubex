from pydantic import Field

from kubex.k8s.v1_38.meta.v1.condition import Condition
from kubex_core.models.base import BaseK8sModel


class CompositePodGroupStatus(BaseK8sModel):
    """CompositePodGroupStatus represents information about the status of a composite pod group."""

    conditions: list[Condition] | None = Field(
        default=None,
        alias="conditions",
        description='conditions represent the latest observations of the CompositePodGroup\'s state. Known condition types: - "CompositePodGroupInitiallyScheduled": Indicates whether the overall scheduling requirement for the subtree under this CompositePodGroup has been satisfied. Once this condition transitions to True, it serves as a terminal state and will never revert to False, even if pods are subsequently deleted and group constraints are no longer met. - "DisruptionTarget": Indicates whether the CompositePodGroup is about to be terminated due to disruption such as preemption. Known reasons for the CompositePodGroupInitiallyScheduled condition: - "Scheduled": All required child groups and pods under this CompositePodGroup have been successfully scheduled. - "Unschedulable": The CompositePodGroup\'s subtree could not be placed, for example due to unmet minGroupCount, placement constraints, or insufficient capacity for its child groups. - "SchedulerError": The CompositePodGroup cannot be scheduled due to some internal error that occurred during scheduling. - "CompositePodGroupError": The CompositePodGroup cannot be scheduled due to an invalid group layout detected during runtime validation. The `message` field details the specific layout violation (such as a detected cycle, exceeding the maximum depth of 4, or referencing multiple distinct Workloads). Known reasons for the DisruptionTarget condition: - "PreemptionByScheduler": The CompositePodGroup was preempted by the scheduler to make room for higher-priority CompositePodGroups, PodGroups or Pods.',
    )
