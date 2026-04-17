from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class PodSchedulingGroup(BaseK8sModel):
    """PodSchedulingGroup identifies the runtime scheduling group instance that a Pod belongs to. The scheduler uses this information to apply workload-aware scheduling semantics. Exactly one field must be specified."""

    pod_group_name: str | None = Field(
        default=None,
        alias="podGroupName",
        description="PodGroupName specifies the name of the standalone PodGroup object that represents the runtime instance of this group. Must be a DNS subdomain.",
    )
