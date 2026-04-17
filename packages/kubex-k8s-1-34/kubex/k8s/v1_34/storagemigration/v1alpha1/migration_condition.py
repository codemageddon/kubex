import datetime

from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class MigrationCondition(BaseK8sModel):
    """Describes the state of a migration at a certain point."""

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
    type_: str = Field(..., alias="type", description="Type of the condition.")
