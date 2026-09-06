from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class ContainerStateWaiting(BaseK8sModel):
    """ContainerStateWaiting is a waiting state of a container."""

    message: str | None = Field(
        default=None,
        alias="message",
        description="Message regarding why the container is not yet running.",
    )
    reason: str | None = Field(
        default=None,
        alias="reason",
        description="(brief) reason the container is not yet running.",
    )
