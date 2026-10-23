from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class ContainerStateWaiting(BaseK8sModel):
    """ContainerStateWaiting is a waiting state of a container."""

    message: str | None = Field(
        default=None,
        alias="message",
        description="message regarding why the container is not yet running.",
    )
    reason: str | None = Field(
        default=None,
        alias="reason",
        description="reason the container is not yet running.",
    )
