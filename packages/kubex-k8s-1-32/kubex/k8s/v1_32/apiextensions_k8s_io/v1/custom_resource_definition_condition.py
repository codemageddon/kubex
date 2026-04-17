import datetime

from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class CustomResourceDefinitionCondition(BaseK8sModel):
    """CustomResourceDefinitionCondition contains details for the current condition of this pod."""

    last_transition_time: datetime.datetime | None = Field(
        default=None,
        alias="lastTransitionTime",
        description="lastTransitionTime last time the condition transitioned from one status to another.",
    )
    message: str | None = Field(
        default=None,
        alias="message",
        description="message is a human-readable message indicating details about last transition.",
    )
    reason: str | None = Field(
        default=None,
        alias="reason",
        description="reason is a unique, one-word, CamelCase reason for the condition's last transition.",
    )
    status: str = Field(
        ...,
        alias="status",
        description="status is the status of the condition. Can be True, False, Unknown.",
    )
    type_: str = Field(
        ...,
        alias="type",
        description="type is the type of the condition. Types include Established, NamesAccepted and Terminating.",
    )
