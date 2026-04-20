import datetime

from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class DeploymentCondition(BaseK8sModel):
    """DeploymentCondition describes the state of a deployment at a certain point."""

    last_transition_time: datetime.datetime | None = Field(
        default=None,
        alias="lastTransitionTime",
        description="Last time the condition transitioned from one status to another.",
    )
    last_update_time: datetime.datetime | None = Field(
        default=None,
        alias="lastUpdateTime",
        description="The last time this condition was updated.",
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
    type_: str = Field(..., alias="type", description="Type of deployment condition.")
