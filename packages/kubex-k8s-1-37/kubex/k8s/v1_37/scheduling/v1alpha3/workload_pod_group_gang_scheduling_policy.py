from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class WorkloadPodGroupGangSchedulingPolicy(BaseK8sModel):
    """WorkloadPodGroupGangSchedulingPolicy defines the parameters for gang (all-or-nothing) scheduling."""

    min_count: int | None = Field(
        default=None,
        alias="minCount",
        description="minCount is the minimum number of pods that must be scheduled at the same time for the scheduler to admit the entire group. This field is optional. If it is not specified, the controller should inject a context-specific sane default (e.g., parallelism for a Job). If set, it must be a positive integer.",
    )
