import datetime

from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class ReplicaSetCondition(BaseK8sModel):
    """ReplicaSetCondition describes the state of a replica set at a certain point."""

    last_transition_time: datetime.datetime | None = Field(
        default=None,
        alias="lastTransitionTime",
        description="lastTransitionTime is the last time the condition transitioned from one status to another.",
    )
    message: str | None = Field(
        default=None,
        alias="message",
        description="message is a human readable string indicating details about the transition.",
    )
    reason: str | None = Field(
        default=None,
        alias="reason",
        description="reason for the condition's last transition.",
    )
    status: str | None = Field(
        default=None,
        alias="status",
        description="status of the condition, one of True, False, Unknown.",
    )
    type_: str | None = Field(
        default=None, alias="type", description="type of replica set condition."
    )
