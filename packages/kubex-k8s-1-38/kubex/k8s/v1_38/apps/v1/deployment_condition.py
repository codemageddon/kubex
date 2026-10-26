from pydantic import Field

from kubex_core.models.base import BaseK8sModel
from kubex_core.models.types import Time


class DeploymentCondition(BaseK8sModel):
    """DeploymentCondition describes the state of a deployment at a certain point."""

    last_transition_time: Time | None = Field(
        default=None,
        alias="lastTransitionTime",
        description="lastTransitionTime is the last time the condition transitioned from one status to another.",
    )
    last_update_time: Time | None = Field(
        default=None,
        alias="lastUpdateTime",
        description="lastUpdateTime is the last time this condition was updated.",
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
        default=None, alias="type", description="type of deployment condition."
    )
