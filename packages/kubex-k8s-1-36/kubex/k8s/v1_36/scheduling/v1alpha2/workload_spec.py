from pydantic import Field

from kubex.k8s.v1_36.scheduling.v1alpha2.pod_group_template import PodGroupTemplate
from kubex.k8s.v1_36.scheduling.v1alpha2.typed_local_object_reference import (
    TypedLocalObjectReference,
)
from kubex_core.models.base import BaseK8sModel


class WorkloadSpec(BaseK8sModel):
    """WorkloadSpec defines the desired state of a Workload."""

    controller_ref: TypedLocalObjectReference | None = Field(
        default=None,
        alias="controllerRef",
        description="ControllerRef is an optional reference to the controlling object, such as a Deployment or Job. This field is intended for use by tools like CLIs to provide a link back to the original workload definition. This field is immutable.",
    )
    pod_group_templates: list[PodGroupTemplate] = Field(
        ...,
        alias="podGroupTemplates",
        description="PodGroupTemplates is the list of templates that make up the Workload. The maximum number of templates is 8. This field is immutable.",
    )
