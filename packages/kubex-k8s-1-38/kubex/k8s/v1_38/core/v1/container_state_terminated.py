from pydantic import Field

from kubex_core.models.base import BaseK8sModel
from kubex_core.models.types import Time


class ContainerStateTerminated(BaseK8sModel):
    """ContainerStateTerminated is a terminated state of a container."""

    container_id: str | None = Field(
        default=None,
        alias="containerID",
        description="containerID is the container's ID in the format '<type>://<container_id>'",
    )
    exit_code: int = Field(
        ...,
        alias="exitCode",
        description="exitCode is the exit status from the last termination of the container",
    )
    finished_at: Time | None = Field(
        default=None,
        alias="finishedAt",
        description="finishedAt is the time at which the container last terminated",
    )
    message: str | None = Field(
        default=None,
        alias="message",
        description="message regarding the last termination of the container",
    )
    reason: str | None = Field(
        default=None,
        alias="reason",
        description="reason from the last termination of the container",
    )
    signal: int | None = Field(
        default=None,
        alias="signal",
        description="signal from the last termination of the container",
    )
    started_at: Time | None = Field(
        default=None,
        alias="startedAt",
        description="startedAt is the time at which previous execution of the container started",
    )
