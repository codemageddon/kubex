from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class ResourceFieldSelector(BaseK8sModel):
    """ResourceFieldSelector represents container resources (cpu, memory) and their output format"""

    container_name: str | None = Field(
        default=None,
        alias="containerName",
        description="Container name: required for volumes, optional for env vars",
    )
    divisor: str | None = Field(
        default=None,
        alias="divisor",
        description='Specifies the output format of the exposed resources, defaults to "1"',
    )
    resource: str = Field(
        ..., alias="resource", description="Required: resource to select"
    )
