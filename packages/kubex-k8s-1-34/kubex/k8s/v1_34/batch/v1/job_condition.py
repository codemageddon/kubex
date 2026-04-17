import datetime

from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class JobCondition(BaseK8sModel):
    """JobCondition describes current state of a job."""

    last_probe_time: datetime.datetime | None = Field(
        default=None,
        alias="lastProbeTime",
        description="Last time the condition was checked.",
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
    type_: str = Field(
        ..., alias="type", description="Type of job condition, Complete or Failed."
    )
