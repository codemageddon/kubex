import datetime

from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class ContainerStateTerminated(BaseK8sModel):
    """ContainerStateTerminated is a terminated state of a container."""

    container_id: str | None = Field(
        default=None,
        alias="containerID",
        description="Container's ID in the format '<type>://<container_id>'",
    )
    exit_code: int = Field(
        ...,
        alias="exitCode",
        description="Exit status from the last termination of the container",
    )
    finished_at: datetime.datetime | None = Field(
        default=None,
        alias="finishedAt",
        description="Time at which the container last terminated",
    )
    message: str | None = Field(
        default=None,
        alias="message",
        description="Message regarding the last termination of the container",
    )
    reason: str | None = Field(
        default=None,
        alias="reason",
        description="(brief) reason from the last termination of the container",
    )
    signal: int | None = Field(
        default=None,
        alias="signal",
        description="Signal from the last termination of the container",
    )
    started_at: datetime.datetime | None = Field(
        default=None,
        alias="startedAt",
        description="Time at which previous execution of the container started",
    )
