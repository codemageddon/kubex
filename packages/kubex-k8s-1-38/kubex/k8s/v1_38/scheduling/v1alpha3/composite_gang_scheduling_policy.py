from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class CompositeGangSchedulingPolicy(BaseK8sModel):
    """CompositeGangSchedulingPolicy indicates that the groups belonging to the composite group should be scheduled using all-or-nothing semantics."""

    min_group_count: int = Field(
        ...,
        alias="minGroupCount",
        description="minGroupCount is the minimum number of child groups that must be schedulable or scheduled at the same time for the scheduler to admit the entire group. It must be a positive integer.",
    )
