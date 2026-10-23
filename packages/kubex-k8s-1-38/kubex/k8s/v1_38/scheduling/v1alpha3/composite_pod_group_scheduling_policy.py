from pydantic import Field

from kubex.k8s.v1_38.scheduling.v1alpha3.composite_basic_scheduling_policy import (
    CompositeBasicSchedulingPolicy,
)
from kubex.k8s.v1_38.scheduling.v1alpha3.composite_gang_scheduling_policy import (
    CompositeGangSchedulingPolicy,
)
from kubex_core.models.base import BaseK8sModel


class CompositePodGroupSchedulingPolicy(BaseK8sModel):
    """CompositePodGroupSchedulingPolicy defines the scheduling configuration for a CompositePodGroup. Exactly one policy must be set. The policy is chosen at creation time by setting either the Basic or Gang field. The CompositePodGroup may not change policy after creation. Fields within chosen policy may be updated after creation when their individual fields allow it."""

    basic: CompositeBasicSchedulingPolicy | None = Field(
        default=None,
        alias="basic",
        description="basic specifies that the groups of this composite group should be scheduled independently. Setting this field at group creation time opts this group to basic scheduling; this field cannot be changed afterward.",
    )
    gang: CompositeGangSchedulingPolicy | None = Field(
        default=None,
        alias="gang",
        description="gang specifies that the groups of this composite group should be scheduled using all-or-nothing semantics. Setting this field at group creation time opts this group to gang scheduling; this field cannot be set or unset afterward. The minGroupCount field within Gang scheduling policy remains mutable after group creation.",
    )
