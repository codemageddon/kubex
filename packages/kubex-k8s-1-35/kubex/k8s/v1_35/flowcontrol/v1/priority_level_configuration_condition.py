import datetime

from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class PriorityLevelConfigurationCondition(BaseK8sModel):
    """PriorityLevelConfigurationCondition defines the condition of priority level."""

    last_transition_time: datetime.datetime | None = Field(
        default=None,
        alias="lastTransitionTime",
        description="`lastTransitionTime` is the last time the condition transitioned from one status to another.",
    )
    message: str | None = Field(
        default=None,
        alias="message",
        description="`message` is a human-readable message indicating details about last transition.",
    )
    reason: str | None = Field(
        default=None,
        alias="reason",
        description="`reason` is a unique, one-word, CamelCase reason for the condition's last transition.",
    )
    status: str | None = Field(
        default=None,
        alias="status",
        description="`status` is the status of the condition. Can be True, False, Unknown. Required.",
    )
    type_: str | None = Field(
        default=None,
        alias="type",
        description="`type` is the type of the condition. Required.",
    )
