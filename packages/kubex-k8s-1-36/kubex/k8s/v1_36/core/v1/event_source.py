from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class EventSource(BaseK8sModel):
    """EventSource contains information for an event."""

    component: str | None = Field(
        default=None,
        alias="component",
        description="Component from which the event is generated.",
    )
    host: str | None = Field(
        default=None,
        alias="host",
        description="Node name on which the event is generated.",
    )
