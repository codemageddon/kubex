from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class ContainerResizePolicy(BaseK8sModel):
    """ContainerResizePolicy represents resource resize policy for the container."""

    resource_name: str = Field(
        ...,
        alias="resourceName",
        description="Name of the resource to which this resource resize policy applies. Supported values: cpu, memory.",
    )
    restart_policy: str = Field(
        ...,
        alias="restartPolicy",
        description="Restart policy to apply when specified resource is resized. If not specified, it defaults to NotRequired.",
    )
