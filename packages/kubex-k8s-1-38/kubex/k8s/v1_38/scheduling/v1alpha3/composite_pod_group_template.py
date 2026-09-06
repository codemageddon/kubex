from __future__ import annotations

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
from kubex.k8s.v1_38.scheduling.v1alpha3.pod_group_template import PodGroupTemplate
from kubex_core.models.base import BaseK8sModel


class CompositePodGroupTemplate(BaseK8sModel):
    """CompositePodGroupTemplate represents a template for a CompositePodGroup with a scheduling policy."""

    composite_pod_group_templates: list[CompositePodGroupTemplate] | None = Field(
        default=None,
        alias="compositePodGroupTemplates",
        description="compositePodGroupTemplates is the list of templates for children CompositePodGroups. The maximum number of templates is 8. At least one entry in CompositePodGroupTemplates or PodGroupTemplates must be set.",
    )
    disruption_mode: CompositeDisruptionMode | None = Field(
        default=None,
        alias="disruptionMode",
        description="disruptionMode defines the mode in which a given CompositePodGroup can be disrupted. One of Single, All. This field is immutable.",
    )
    name: str = Field(
        ...,
        alias="name",
        description="name is a unique identifier for the CompositePodGroupTemplate within the Workload. It must be a DNS label. This field is required.",
    )
    pod_group_templates: list[PodGroupTemplate] | None = Field(
        default=None,
        alias="podGroupTemplates",
        description="podGroupTemplates is the list of templates for children PodGroups. The maximum number of templates is 8. At least one entry in CompositePodGroupTemplates or PodGroupTemplates must be set.",
    )
    preemption_policy: str | None = Field(
        default=None,
        alias="preemptionPolicy",
        description="preemptionPolicy is the Policy for preempting pods/podgroups with lower priority. One of Never, PreemptLowerPriority. This field is immutable. This field is available only when the PodGroupPreemptionPolicy feature gate is enabled.",
    )
    priority: int | None = Field(
        default=None,
        alias="priority",
        description="priority is the value of priority of composite pod groups created from this template. Various system components use this field to find the priority of the composite pod group. When Priority Admission Controller is enabled, it prevents users from setting this field. The admission controller populates this field from PriorityClassName. The higher the value, the higher the priority. This field is immutable.",
    )
    priority_class_name: str | None = Field(
        default=None,
        alias="priorityClassName",
        description="priorityClassName indicates the priority that should be considered when scheduling a composite pod group created from this template. If no priority class is specified, admission control can set this to the global default priority class if it exists. Otherwise, composite pod groups created from this template will have the priority set to zero. This field is immutable.",
    )
    scheduling_constraints: CompositePodGroupSchedulingConstraints | None = Field(
        default=None,
        alias="schedulingConstraints",
        description="schedulingConstraints defines optional scheduling constraints (e.g. topology) for this CompositePodGroupTemplate. This field is immutable.",
    )
    scheduling_policy: CompositePodGroupSchedulingPolicy = Field(
        ...,
        alias="schedulingPolicy",
        description="schedulingPolicy defines the scheduling policy for this template.",
    )
