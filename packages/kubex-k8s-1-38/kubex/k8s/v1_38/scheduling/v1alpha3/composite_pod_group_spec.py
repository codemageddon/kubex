from pydantic import Field

from kubex.k8s.v1_38.scheduling.v1alpha3.composite_disruption_mode import (
    CompositeDisruptionMode,
)
from kubex.k8s.v1_38.scheduling.v1alpha3.composite_pod_group_scheduling_constraints import (
    CompositePodGroupSchedulingConstraints,
)
from kubex.k8s.v1_38.scheduling.v1alpha3.composite_pod_group_scheduling_policy import (
    CompositePodGroupSchedulingPolicy,
)
from kubex.k8s.v1_38.scheduling.v1alpha3.workload_reference import WorkloadReference
from kubex_core.models.base import BaseK8sModel


class CompositePodGroupSpec(BaseK8sModel):
    """CompositePodGroupSpec defines the desired state of CompositePodGroup."""

    disruption_mode: CompositeDisruptionMode | None = Field(
        default=None,
        alias="disruptionMode",
        description="disruptionMode defines the mode in which a given CompositePodGroup can be disrupted. Controllers are expected to fill this field by copying it from a CompositePodGroupTemplate. One of Single, All. Defaults to Single if unset. This field is immutable.",
    )
    parent_composite_pod_group_name: str | None = Field(
        default=None,
        alias="parentCompositePodGroupName",
        description="parentCompositePodGroupName contains the name of the parent composite pod group within the same namespace as this composite pod group. It must be a DNS name. If it's nil, then this composite pod group is a root of a workload's hierarchy. This field is immutable.",
    )
    preemption_policy: str | None = Field(
        default=None,
        alias="preemptionPolicy",
        description="preemptionPolicy is the Policy for preempting pods/podgroups with lower priority. One of Never, PreemptLowerPriority. Defaults to PreemptLowerPriority if unset. When Priority Admission Controller is enabled, it populates this field from PriorityClassName, and defaults to PreemptLowerPriority if value is unset in PriorityClass. This field is immutable. This field is available only when the PodGroupPreemptionPolicy feature gate is enabled.",
    )
    priority: int | None = Field(
        default=None,
        alias="priority",
        description="priority is the value of priority of this composite pod group. Various system components use this field to find the priority of the composite pod group. When Priority Admission Controller is enabled, it prevents users from setting this field. The admission controller populates this field from PriorityClassName. The higher the value, the higher the priority. This field is immutable.",
    )
    priority_class_name: str | None = Field(
        default=None,
        alias="priorityClassName",
        description="priorityClassName defines the priority that should be considered when scheduling this CompositePodGroup. Controllers are expected to fill this field by copying it from a CompositePodGroupTemplate. If left unspecified, it is validated and resolved similarly to the PriorityClassName field in Pods (i.e. if no priority class is specified, admission control can set this to the global default priority class if it exists. Otherwise, the composite pod group's priority will be zero). This field is immutable.",
    )
    scheduling_constraints: CompositePodGroupSchedulingConstraints | None = Field(
        default=None,
        alias="schedulingConstraints",
        description="schedulingConstraints defines optional scheduling constraints (e.g. topology) for this CompositePodGroup. Controllers are expected to fill this field by copying it from a CompositePodGroupTemplate. This field is immutable.",
    )
    scheduling_policy: CompositePodGroupSchedulingPolicy = Field(
        ...,
        alias="schedulingPolicy",
        description="schedulingPolicy defines the scheduling policy for this instance of the CompositePodGroup. Controllers are expected to fill this field by copying it from a CompositePodGroupTemplate. This field is immutable.",
    )
    workload_ref: WorkloadReference = Field(
        ...,
        alias="workloadRef",
        description="workloadRef references an optional CompositePodGroup template within the Workload object that was used to create the CompositePodGroup. This field is required. This field is immutable.",
    )
