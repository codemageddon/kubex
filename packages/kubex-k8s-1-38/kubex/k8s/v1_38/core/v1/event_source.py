from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class EventSource(BaseK8sModel):
    """EventSource contains information for an event."""

    component: str | None = Field(
        default=None,
        alias="component",
        description="component from which the event is generated.",
    )
    host: str | None = Field(
        default=None,
        alias="host",
        description="host name on which the event is generated.",
    )
