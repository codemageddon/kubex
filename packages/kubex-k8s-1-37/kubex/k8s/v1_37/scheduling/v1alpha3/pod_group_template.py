from pydantic import Field

from kubex.k8s.v1_37.scheduling.v1alpha3.disruption_mode import DisruptionMode
from kubex.k8s.v1_37.scheduling.v1alpha3.pod_group_resource_claim import (
    PodGroupResourceClaim,
)
from kubex.k8s.v1_37.scheduling.v1alpha3.pod_group_scheduling_constraints import (
    PodGroupSchedulingConstraints,
)
from kubex.k8s.v1_37.scheduling.v1alpha3.pod_group_scheduling_policy import (
    PodGroupSchedulingPolicy,
)
from kubex_core.models.base import BaseK8sModel


class PodGroupTemplate(BaseK8sModel):
    """PodGroupTemplate represents a template for a set of pods with a scheduling policy."""

    disruption_mode: DisruptionMode | None = Field(
        default=None,
        alias="disruptionMode",
        description="disruptionMode defines the mode in which a given PodGroup can be disrupted. One of Single, All. This field is immutable.",
    )
    name: str = Field(
        ...,
        alias="name",
        description="name is a unique identifier for the PodGroupTemplate within the Workload. It must be a DNS label. This field is immutable.",
    )
    preemption_policy: str | None = Field(
        default=None,
        alias="preemptionPolicy",
        description="preemptionPolicy is the Policy for preempting pods/podgroups with lower priority. One of Never, PreemptLowerPriority. This field is immutable. This field is available only when the PodGroupPreemptionPolicy feature gate is enabled.",
    )
    priority: int | None = Field(
        default=None,
        alias="priority",
        description="priority is the value of priority of pod groups created from this template. Various system components use this field to find the priority of the pod group. The higher the value, the higher the priority. This field is immutable.",
    )
    priority_class_name: str | None = Field(
        default=None,
        alias="priorityClassName",
        description="priorityClassName indicates the priority that should be considered when scheduling a pod group created from this template. This field is immutable.",
    )
    resource_claims: list[PodGroupResourceClaim] | None = Field(
        default=None,
        alias="resourceClaims",
        description="resourceClaims defines which ResourceClaims may be shared among Pods in the group. Pods consume the devices allocated to a PodGroup's claim by defining a claim in its own Spec.ResourceClaims that matches the PodGroup's claim exactly. The claim must have the same name and refer to the same ResourceClaim or ResourceClaimTemplate. This is a beta-level field and requires that the DRAWorkloadResourceClaims feature gate is enabled. This field is immutable.",
    )
    scheduling_constraints: PodGroupSchedulingConstraints | None = Field(
        default=None,
        alias="schedulingConstraints",
        description="schedulingConstraints defines optional scheduling constraints (e.g. topology) for this PodGroupTemplate. This field is only available when the TopologyAwareWorkloadScheduling feature gate is enabled. This field is immutable.",
    )
    scheduling_policy: PodGroupSchedulingPolicy = Field(
        ...,
        alias="schedulingPolicy",
        description="schedulingPolicy defines the scheduling policy for this PodGroupTemplate.",
    )
