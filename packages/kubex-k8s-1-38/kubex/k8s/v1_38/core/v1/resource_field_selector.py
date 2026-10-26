from pydantic import Field

from kubex_core.models.base import BaseK8sModel
from kubex_core.models.types import Quantity


class ResourceFieldSelector(BaseK8sModel):
    """ResourceFieldSelector represents container resources (cpu, memory) and their output format"""

    container_name: str | None = Field(
        default=None,
        alias="containerName",
        description="containerName is the name of the container: required for volumes, optional for env vars",
    )
    divisor: Quantity | None = Field(
        default=None,
        alias="divisor",
        description="divisor optionally indicates how the resource from the container should be scaled. If unset or 0, the resource is not scaled (divisor is treated as 1).",
    )
    resource: str = Field(
        ..., alias="resource", description="resource is the resource to select"
    )
