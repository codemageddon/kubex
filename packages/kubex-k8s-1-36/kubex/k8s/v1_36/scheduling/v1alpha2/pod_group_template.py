from kubex.k8s.v1_36.scheduling.v1alpha2.pod_group_resource_claim import (
    PodGroupResourceClaim,
)
from kubex.k8s.v1_36.scheduling.v1alpha2.pod_group_scheduling_constraints import (
    PodGroupSchedulingConstraints,
)
from kubex.k8s.v1_36.scheduling.v1alpha2.pod_group_scheduling_policy import (
    PodGroupSchedulingPolicy,
)
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class PodGroupTemplate(BaseK8sModel):
    """PodGroupTemplate represents a template for a set of pods with a scheduling policy."""

    disruption_mode: str | None = Field(
        default=None,
        alias="disruptionMode",
        description="DisruptionMode defines the mode in which a given PodGroup can be disrupted. One of Pod, PodGroup. This field is available only when the WorkloadAwarePreemption feature gate is enabled.",
    )
    name: str = Field(
        ...,
        alias="name",
        description="Name is a unique identifier for the PodGroupTemplate within the Workload. It must be a DNS label. This field is immutable.",
    )
    priority: int | None = Field(
        default=None,
        alias="priority",
        description="Priority is the value of priority of pod groups created from this template. Various system components use this field to find the priority of the pod group. When Priority Admission Controller is enabled, it prevents users from setting this field. The admission controller populates this field from PriorityClassName. The higher the value, the higher the priority. This field is available only when the WorkloadAwarePreemption feature gate is enabled.",
    )
    priority_class_name: str | None = Field(
        default=None,
        alias="priorityClassName",
        description="PriorityClassName indicates the priority that should be considered when scheduling a pod group created from this template. If no priority class is specified, admission control can set this to the global default priority class if it exists. Otherwise, pod groups created from this template will have the priority set to zero. This field is available only when the WorkloadAwarePreemption feature gate is enabled.",
    )
    resource_claims: list[PodGroupResourceClaim] | None = Field(
        default=None,
        alias="resourceClaims",
        description="ResourceClaims defines which ResourceClaims may be shared among Pods in the group. Pods consume the devices allocated to a PodGroup's claim by defining a claim in its own Spec.ResourceClaims that matches the PodGroup's claim exactly. The claim must have the same name and refer to the same ResourceClaim or ResourceClaimTemplate. This is an alpha-level field and requires that the DRAWorkloadResourceClaims feature gate is enabled. This field is immutable.",
    )
    scheduling_constraints: PodGroupSchedulingConstraints | None = Field(
        default=None,
        alias="schedulingConstraints",
        description="SchedulingConstraints defines optional scheduling constraints (e.g. topology) for this PodGroupTemplate. This field is only available when the TopologyAwareWorkloadScheduling feature gate is enabled.",
    )
    scheduling_policy: PodGroupSchedulingPolicy = Field(
        ...,
        alias="schedulingPolicy",
        description="SchedulingPolicy defines the scheduling policy for this PodGroupTemplate.",
    )
