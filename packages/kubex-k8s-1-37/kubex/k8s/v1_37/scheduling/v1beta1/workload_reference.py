from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class WorkloadReference(BaseK8sModel):
    """WorkloadReference references the Workload object together with the template that was used to create a particular PodGroup."""

    template_name: str = Field(
        ...,
        alias="templateName",
        description="templateName is the name of a template within the Workload object that was used to create a pod group. It must be a DNS label. This field is required.",
    )
    workload_name: str = Field(
        ...,
        alias="workloadName",
        description="workloadName is the name of the Workload object that contains a template that was used when creating a pod group. It must be a DNS name. This field is required.",
    )
