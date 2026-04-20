from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class GangSchedulingPolicy(BaseK8sModel):
    """GangSchedulingPolicy defines the parameters for gang scheduling."""

    min_count: int = Field(
        ...,
        alias="minCount",
        description="MinCount is the minimum number of pods that must be schedulable or scheduled at the same time for the scheduler to admit the entire group. It must be a positive integer.",
    )
