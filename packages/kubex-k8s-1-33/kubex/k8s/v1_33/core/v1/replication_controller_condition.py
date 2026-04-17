import datetime

from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class ReplicationControllerCondition(BaseK8sModel):
    """ReplicationControllerCondition describes the state of a replication controller at a certain point."""

    last_transition_time: datetime.datetime | None = Field(
        default=None,
        alias="lastTransitionTime",
        description="The last time the condition transitioned from one status to another.",
    )
    message: str | None = Field(
        default=None,
        alias="message",
        description="A human readable message indicating details about the transition.",
    )
    reason: str | None = Field(
        default=None,
        alias="reason",
        description="The reason for the condition's last transition.",
    )
    status: str = Field(
        ...,
        alias="status",
        description="Status of the condition, one of True, False, Unknown.",
    )
    type_: str = Field(
        ..., alias="type", description="Type of replication controller condition."
    )
