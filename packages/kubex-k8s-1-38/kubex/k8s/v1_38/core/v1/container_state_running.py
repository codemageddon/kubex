from pydantic import Field

from kubex_core.models.base import BaseK8sModel
from kubex_core.models.types import Time


class ContainerStateRunning(BaseK8sModel):
    """ContainerStateRunning is a running state of a container."""

    started_at: Time | None = Field(
        default=None,
        alias="startedAt",
        description="startedAt is the time at which the container was last (re-)started",
    )
