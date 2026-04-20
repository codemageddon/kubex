import datetime

from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class StorageVersionCondition(BaseK8sModel):
    """Describes the state of the storageVersion at a certain point."""

    last_transition_time: datetime.datetime | None = Field(
        default=None,
        alias="lastTransitionTime",
        description="Last time the condition transitioned from one status to another.",
    )
    message: str = Field(
        ...,
        alias="message",
        description="A human readable message indicating details about the transition.",
    )
    observed_generation: int | None = Field(
        default=None,
        alias="observedGeneration",
        description="If set, this represents the .metadata.generation that the condition was set based upon.",
    )
    reason: str = Field(
        ...,
        alias="reason",
        description="The reason for the condition's last transition.",
    )
    status: str = Field(
        ...,
        alias="status",
        description="Status of the condition, one of True, False, Unknown.",
    )
    type_: str = Field(..., alias="type", description="Type of the condition.")
