from pydantic import Field

from kubex.k8s.v1_37.scheduling.v1alpha2.pod_group_resource_claim import (
    PodGroupResourceClaim,
)
from kubex.k8s.v1_37.scheduling.v1alpha2.pod_group_scheduling_constraints import (
    PodGroupSchedulingConstraints,
)
from kubex.k8s.v1_37.scheduling.v1alpha2.pod_group_scheduling_policy import (
    PodGroupSchedulingPolicy,
)
from kubex.k8s.v1_37.scheduling.v1alpha2.pod_group_template_reference import (
    PodGroupTemplateReference,
)
from kubex_core.models.base import BaseK8sModel


class PodGroupSpec(BaseK8sModel):
    """PodGroupSpec defines the desired state of a PodGroup."""

    disruption_mode: str | None = Field(
        default=None,
        alias="disruptionMode",
        description="DisruptionMode defines the mode in which a given PodGroup can be disrupted. Controllers are expected to fill this field by copying it from a PodGroupTemplate. One of Pod, PodGroup. Defaults to Pod if unset. This field is immutable. This field is available only when the WorkloadAwarePreemption feature gate is enabled.",
    )
    pod_group_template_ref: PodGroupTemplateReference | None = Field(
        default=None,
        alias="podGroupTemplateRef",
        description="PodGroupTemplateRef references an optional PodGroup template within other object (e.g. Workload) that was used to create the PodGroup. This field is immutable.",
    )
    priority: int | None = Field(
        default=None,
        alias="priority",
        description="Priority is the value of priority of this pod group. Various system components use this field to find the priority of the pod group. When Priority Admission Controller is enabled, it prevents users from setting this field. The admission controller populates this field from PriorityClassName. The higher the value, the higher the priority. This field is immutable. This field is available only when the WorkloadAwarePreemption feature gate is enabled.",
    )
    priority_class_name: str | None = Field(
        default=None,
        alias="priorityClassName",
        description="PriorityClassName defines the priority that should be considered when scheduling this pod group. Controllers are expected to fill this field by copying it from a PodGroupTemplate. Otherwise, it is validated and resolved similarly to the PriorityClassName on PodGroupTemplate (i.e. if no priority class is specified, admission control can set this to the global default priority class if it exists. Otherwise, the pod group's priority will be zero). This field is immutable. This field is available only when the WorkloadAwarePreemption feature gate is enabled.",
    )
    resource_claims: list[PodGroupResourceClaim] | None = Field(
        default=None,
        alias="resourceClaims",
        description="ResourceClaims defines which ResourceClaims may be shared among Pods in the group. Pods consume the devices allocated to a PodGroup's claim by defining a claim in its own Spec.ResourceClaims that matches the PodGroup's claim exactly. The claim must have the same name and refer to the same ResourceClaim or ResourceClaimTemplate. This is an alpha-level field and requires that the DRAWorkloadResourceClaims feature gate is enabled. This field is immutable.",
    )
    scheduling_constraints: PodGroupSchedulingConstraints | None = Field(
        default=None,
        alias="schedulingConstraints",
        description="SchedulingConstraints defines optional scheduling constraints (e.g. topology) for this PodGroup. Controllers are expected to fill this field by copying it from a PodGroupTemplate. This field is immutable. This field is only available when the TopologyAwareWorkloadScheduling feature gate is enabled.",
    )
    scheduling_policy: PodGroupSchedulingPolicy = Field(
        ...,
        alias="schedulingPolicy",
        description="SchedulingPolicy defines the scheduling policy for this instance of the PodGroup. Controllers are expected to fill this field by copying it from a PodGroupTemplate. This field is immutable.",
    )
