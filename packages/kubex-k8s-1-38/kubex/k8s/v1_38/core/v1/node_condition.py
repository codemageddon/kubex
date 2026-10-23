import datetime

from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class NodeCondition(BaseK8sModel):
    """NodeCondition contains condition information for a node."""

    last_heartbeat_time: datetime.datetime | None = Field(
        default=None,
        alias="lastHeartbeatTime",
        description="lastHeartbeatTime is the last time we got an update on a given condition.",
    )
    last_transition_time: datetime.datetime | None = Field(
        default=None,
        alias="lastTransitionTime",
        description="lastTransitionTime is the last time the condition transit from one status to another.",
    )
    message: str | None = Field(
        default=None,
        alias="message",
        description="message is a human readable message indicating details about last transition.",
    )
    reason: str | None = Field(
        default=None,
        alias="reason",
        description="reason is the (brief) reason for the condition's last transition.",
    )
    status: str = Field(
        ...,
        alias="status",
        description="status is the status of the condition, one of True, False, Unknown.",
    )
    type_: str = Field(
        ..., alias="type", description="type is the type of node condition."
    )
