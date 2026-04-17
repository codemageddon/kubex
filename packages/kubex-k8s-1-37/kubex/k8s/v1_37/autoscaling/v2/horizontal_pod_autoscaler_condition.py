import datetime

from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class HorizontalPodAutoscalerCondition(BaseK8sModel):
    """HorizontalPodAutoscalerCondition describes the state of a HorizontalPodAutoscaler at a certain point."""

    last_transition_time: datetime.datetime | None = Field(
        default=None,
        alias="lastTransitionTime",
        description="lastTransitionTime is the last time the condition transitioned from one status to another",
    )
    message: str | None = Field(
        default=None,
        alias="message",
        description="message is a human-readable explanation containing details about the transition",
    )
    reason: str | None = Field(
        default=None,
        alias="reason",
        description="reason is the reason for the condition's last transition.",
    )
    status: str = Field(
        ...,
        alias="status",
        description="status is the status of the condition (True, False, Unknown)",
    )
    type_: str = Field(
        ..., alias="type", description="type describes the current condition"
    )
