import datetime

from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class ContainerStateRunning(BaseK8sModel):
    """ContainerStateRunning is a running state of a container."""

    started_at: datetime.datetime | None = Field(
        default=None,
        alias="startedAt",
        description="Time at which the container was last (re-)started",
    )
