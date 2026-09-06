from pydantic import Field

from kubex.k8s.v1_38.scheduling.v1alpha3.composite_basic_scheduling_policy import (
    CompositeBasicSchedulingPolicy,
)
from kubex.k8s.v1_38.scheduling.v1alpha3.composite_gang_scheduling_policy import (
    CompositeGangSchedulingPolicy,
)
from kubex_core.models.base import BaseK8sModel


class CompositePodGroupSchedulingPolicy(BaseK8sModel):
    """CompositePodGroupSchedulingPolicy defines the scheduling configuration for a CompositePodGroup. Exactly one policy must be set."""

    basic: CompositeBasicSchedulingPolicy | None = Field(
        default=None,
        alias="basic",
        description="basic specifies that the groups of this composite group should be scheduled independently. This field is immutable.",
    )
    gang: CompositeGangSchedulingPolicy | None = Field(
        default=None,
        alias="gang",
        description="gang specifies that the groups of this composite group should be scheduled using all-or-nothing semantics.",
    )
