from pydantic import Field

from kubex.k8s.v1_37.scheduling.v1alpha3.composite_pod_group_template import (
    CompositePodGroupTemplate,
)
from kubex.k8s.v1_37.scheduling.v1alpha3.pod_group_template import PodGroupTemplate
from kubex.k8s.v1_37.scheduling.v1alpha3.typed_local_object_reference import (
    TypedLocalObjectReference,
)
from kubex_core.models.base import BaseK8sModel


class WorkloadSpec(BaseK8sModel):
    """WorkloadSpec defines the desired state of a Workload."""

    composite_pod_group_templates: list[CompositePodGroupTemplate] | None = Field(
        default=None,
        alias="compositePodGroupTemplates",
        description="compositePodGroupTemplates is the list of CompositePodGroup templates that make up the Workload. The maximum number of templates is 8. This field is immutable. Exactly one of CompositePodGroupTemplates and PodGroupTemplates must be set. This field is used only when the CompositePodGroup feature gate is enabled.",
    )
    controller_ref: TypedLocalObjectReference | None = Field(
        default=None,
        alias="controllerRef",
        description="controllerRef is an optional reference to the controlling object, such as a Deployment or Job. This field is intended for use by tools like CLIs to provide a link back to the original workload definition. This field is immutable.",
    )
    pod_group_templates: list[PodGroupTemplate] | None = Field(
        default=None,
        alias="podGroupTemplates",
        description="podGroupTemplates is the list of templates that make up the Workload. The maximum number of templates is 8. Templates cannot be added or removed after the workload is created. Existing templates may still be updated where their individual fields allow it. Exactly one of CompositePodGroupTemplates and PodGroupTemplates must be set.",
    )
