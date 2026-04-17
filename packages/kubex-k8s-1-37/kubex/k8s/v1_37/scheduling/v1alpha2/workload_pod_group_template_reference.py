from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class WorkloadPodGroupTemplateReference(BaseK8sModel):
    """WorkloadPodGroupTemplateReference references the PodGroupTemplate within the Workload object."""

    pod_group_template_name: str = Field(
        ...,
        alias="podGroupTemplateName",
        description="PodGroupTemplateName defines the PodGroupTemplate name within the Workload object.",
    )
    workload_name: str = Field(
        ...,
        alias="workloadName",
        description="WorkloadName defines the name of the Workload object.",
    )
