import datetime

from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class StorageVersionCondition(BaseK8sModel):
    """Describes the state of the storageVersion at a certain point."""

    last_transition_time: datetime.datetime | None = Field(
        default=None,
        alias="lastTransitionTime",
        description="lastTransitionTime is the last time the condition transitioned from one status to another.",
    )
    message: str = Field(
        ...,
        alias="message",
        description="message is a human readable string indicating details about the transition.",
    )
    observed_generation: int | None = Field(
        default=None,
        alias="observedGeneration",
        description="observedGeneration represents the .metadata.generation that the condition was set based upon, if field is set.",
    )
    reason: str = Field(
        ..., alias="reason", description="reason for the condition's last transition."
    )
    status: str = Field(
        ...,
        alias="status",
        description="status of the condition, one of True, False, Unknown.",
    )
    type_: str = Field(..., alias="type", description="type of the condition.")
