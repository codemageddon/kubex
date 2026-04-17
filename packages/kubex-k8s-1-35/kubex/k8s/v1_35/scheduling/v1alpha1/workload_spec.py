from kubex.k8s.v1_35.scheduling.v1alpha1.pod_group import PodGroup
from kubex.k8s.v1_35.scheduling.v1alpha1.typed_local_object_reference import (
    TypedLocalObjectReference,
)
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class WorkloadSpec(BaseK8sModel):
    """WorkloadSpec defines the desired state of a Workload."""

    controller_ref: TypedLocalObjectReference | None = Field(
        default=None,
        alias="controllerRef",
        description="ControllerRef is an optional reference to the controlling object, such as a Deployment or Job. This field is intended for use by tools like CLIs to provide a link back to the original workload definition. When set, it cannot be changed.",
    )
    pod_groups: list[PodGroup] = Field(
        ...,
        alias="podGroups",
        description="PodGroups is the list of pod groups that make up the Workload. The maximum number of pod groups is 8. This field is immutable.",
    )
