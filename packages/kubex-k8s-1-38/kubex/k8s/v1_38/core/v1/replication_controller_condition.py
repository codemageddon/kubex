import datetime

from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class ReplicationControllerCondition(BaseK8sModel):
    """ReplicationControllerCondition describes the state of a replication controller at a certain point."""

    last_transition_time: datetime.datetime | None = Field(
        default=None,
        alias="lastTransitionTime",
        description="lastTransitionTime is the last time the condition transitioned from one status to another.",
    )
    message: str | None = Field(
        default=None,
        alias="message",
        description="message is a human readable message indicating details about the transition.",
    )
    reason: str | None = Field(
        default=None,
        alias="reason",
        description="reason is the reason for the condition's last transition.",
    )
    status: str = Field(
        ...,
        alias="status",
        description="status of the condition, one of True, False, Unknown.",
    )
    type_: str = Field(
        ...,
        alias="type",
        description="type is the type of replication controller condition.",
    )
