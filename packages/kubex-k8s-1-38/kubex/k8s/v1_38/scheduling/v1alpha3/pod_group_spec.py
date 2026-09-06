from pydantic import Field

from kubex.k8s.v1_38.scheduling.v1alpha3.disruption_mode import DisruptionMode
from kubex.k8s.v1_38.scheduling.v1alpha3.pod_group_resource_claim import (
    PodGroupResourceClaim,
)
from kubex.k8s.v1_38.scheduling.v1alpha3.pod_group_scheduling_constraints import (
    PodGroupSchedulingConstraints,
)
from kubex.k8s.v1_38.scheduling.v1alpha3.pod_group_scheduling_policy import (
    PodGroupSchedulingPolicy,
)
from kubex.k8s.v1_38.scheduling.v1alpha3.workload_reference import WorkloadReference
from kubex_core.models.base import BaseK8sModel


class PodGroupSpec(BaseK8sModel):
    """PodGroupSpec defines the desired state of a PodGroup."""

    disruption_mode: DisruptionMode | None = Field(
        default=None,
        alias="disruptionMode",
        description="disruptionMode defines the mode in which a given PodGroup can be disrupted. Controllers are expected to fill this field by copying it from a PodGroupTemplate. One of Single, All. Defaults to Single if unset. This field is immutable.",
    )
    parent_composite_pod_group_name: str | None = Field(
        default=None,
        alias="parentCompositePodGroupName",
        description="parentCompositePodGroupName contains the name of the parent composite pod group within the same namespace as this pod group. If it's nil, then this pod group is a root of a workload's hierarchy. This field is used only when the CompositePodGroup feature gate is enabled. This field is immutable.",
    )
    preemption_policy: str | None = Field(
        default=None,
        alias="preemptionPolicy",
        description="preemptionPolicy is the Policy for preempting pods/podgroups with lower priority. One of Never, PreemptLowerPriority. Defaults to PreemptLowerPriority if unset. When Priority Admission Controller is enabled, it populates this field from PriorityClassName, and defaults to PreemptLowerPriority if value is unset in PriorityClass. This field is immutable. This field is available only when the PodGroupPreemptionPolicy feature gate is enabled.",
    )
    priority: int | None = Field(
        default=None,
        alias="priority",
        description="priority is the value of priority of this pod group. Various system components use this field to find the priority of the pod group. When Priority Admission Controller is enabled, it prevents users from setting this field. The admission controller populates this field from PriorityClassName. The higher the value, the higher the priority. This field is immutable.",
    )
    priority_class_name: str | None = Field(
        default=None,
        alias="priorityClassName",
        description="priorityClassName defines the priority that should be considered when scheduling this pod group. Controllers are expected to fill this field by copying it from a PodGroupTemplate. Otherwise, it is validated and resolved similarly to the PriorityClassName on PodGroupTemplate (i.e. if no priority class is specified, admission control can set this to the global default priority class if it exists. Otherwise, the pod group's priority will be zero). This field is immutable.",
    )
    resource_claims: list[PodGroupResourceClaim] | None = Field(
        default=None,
        alias="resourceClaims",
        description="resourceClaims defines which ResourceClaims may be shared among Pods in the group. Pods consume the devices allocated to a PodGroup's claim by defining a claim in its own Spec.ResourceClaims that matches the PodGroup's claim exactly. The claim must have the same name and refer to the same ResourceClaim or ResourceClaimTemplate. This is a beta-level field and requires that the DRAWorkloadResourceClaims feature gate is enabled. This field is immutable.",
    )
    scheduling_constraints: PodGroupSchedulingConstraints | None = Field(
        default=None,
        alias="schedulingConstraints",
        description="schedulingConstraints defines optional scheduling constraints (e.g. topology) for this PodGroup. Controllers are expected to fill this field by copying it from a PodGroupTemplate. This field is immutable. This field is only available when the TopologyAwareWorkloadScheduling feature gate is enabled.",
    )
    scheduling_policy: PodGroupSchedulingPolicy = Field(
        ...,
        alias="schedulingPolicy",
        description="schedulingPolicy defines the scheduling policy for this instance of the PodGroup. Controllers are expected to fill this field by copying it from a PodGroupTemplate.",
    )
    workload_ref: WorkloadReference | None = Field(
        default=None,
        alias="workloadRef",
        description="workloadRef references an optional PodGroup template within the Workload object that was used to create the PodGroup. This field is immutable.",
    )
