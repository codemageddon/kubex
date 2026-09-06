from pydantic import Field

from kubex.k8s.v1_38.scheduling.v1alpha3.workload_pod_group_disruption_mode import (
    WorkloadPodGroupDisruptionMode,
)
from kubex.k8s.v1_38.scheduling.v1alpha3.workload_pod_group_resource_claim import (
    WorkloadPodGroupResourceClaim,
)
from kubex.k8s.v1_38.scheduling.v1alpha3.workload_pod_group_scheduling_constraints import (
    WorkloadPodGroupSchedulingConstraints,
)
from kubex.k8s.v1_38.scheduling.v1alpha3.workload_pod_group_scheduling_policy import (
    WorkloadPodGroupSchedulingPolicy,
)
from kubex_core.models.base import BaseK8sModel


class JobSchedulingConfiguration(BaseK8sModel):
    """JobSchedulingConfiguration composes the reusable workload-aware scheduling building blocks."""

    disruption_mode: WorkloadPodGroupDisruptionMode | None = Field(
        default=None,
        alias="disruptionMode",
        description="DisruptionMode defines the mode in which the Job's pods can be disrupted. One of Single, All. This field is immutable after creation: it may not be added or removed, and the selected mode may not be changed.",
    )
    resource_claims: list[WorkloadPodGroupResourceClaim] | None = Field(
        default=None,
        alias="resourceClaims",
        description="ResourceClaims defines which ResourceClaims may be shared among Pods in the Job. Pods consume the devices allocated to a PodGroup's claim by defining a claim in its own Spec.ResourceClaims that matches the PodGroup's claim exactly. The claim must have the same name and refer to the same ResourceClaim or ResourceClaimTemplate. At most 4 claims may be set, matching the limit on the resulting PodGroup. This list is immutable after creation: entries may neither be added, removed, nor modified.",
    )
    scheduling_constraints: WorkloadPodGroupSchedulingConstraints | None = Field(
        default=None,
        alias="schedulingConstraints",
        description="SchedulingConstraints defines scheduling constraints (e.g. topology) for the Job's pods. This field is immutable after creation.",
    )
    scheduling_policy: WorkloadPodGroupSchedulingPolicy | None = Field(
        default=None,
        alias="schedulingPolicy",
        description="SchedulingPolicy defines the scheduling policy for this Job. Exactly one of Basic or Gang must be set. This field is immutable after creation: the policy may not be added or removed. The policy variant (basic/gang) is frozen by hand-written validation; only schedulingPolicy.gang.minCount may be changed.",
    )
