import datetime

from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class NodeCondition(BaseK8sModel):
    """NodeCondition contains condition information for a node."""

    last_heartbeat_time: datetime.datetime | None = Field(
        default=None,
        alias="lastHeartbeatTime",
        description="Last time we got an update on a given condition.",
    )
    last_transition_time: datetime.datetime | None = Field(
        default=None,
        alias="lastTransitionTime",
        description="Last time the condition transit from one status to another.",
    )
    message: str | None = Field(
        default=None,
        alias="message",
        description="Human readable message indicating details about last transition.",
    )
    reason: str | None = Field(
        default=None,
        alias="reason",
        description="(brief) reason for the condition's last transition.",
    )
    status: str = Field(
        ...,
        alias="status",
        description="Status of the condition, one of True, False, Unknown.",
    )
    type_: str = Field(..., alias="type", description="Type of node condition.")
