import datetime

from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class APIServiceCondition(BaseK8sModel):
    """APIServiceCondition describes the state of an APIService at a particular point"""

    last_transition_time: datetime.datetime | None = Field(
        default=None,
        alias="lastTransitionTime",
        description="Last time the condition transitioned from one status to another.",
    )
    message: str | None = Field(
        default=None,
        alias="message",
        description="Human-readable message indicating details about last transition.",
    )
    reason: str | None = Field(
        default=None,
        alias="reason",
        description="Unique, one-word, CamelCase reason for the condition's last transition.",
    )
    status: str = Field(
        ...,
        alias="status",
        description="Status is the status of the condition. Can be True, False, Unknown.",
    )
    type_: str = Field(
        ..., alias="type", description="Type is the type of the condition."
    )
