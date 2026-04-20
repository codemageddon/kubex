from pydantic import Field

from kubex.k8s.v1_36.scheduling.v1alpha2.workload_pod_group_template_reference import (
    WorkloadPodGroupTemplateReference,
)
from kubex_core.models.base import BaseK8sModel


class PodGroupTemplateReference(BaseK8sModel):
    """PodGroupTemplateReference references a PodGroup template defined in some object (e.g. Workload). Exactly one reference must be set."""

    workload: WorkloadPodGroupTemplateReference | None = Field(
        default=None,
        alias="workload",
        description="Workload references the PodGroupTemplate within the Workload object that was used to create the PodGroup.",
    )
