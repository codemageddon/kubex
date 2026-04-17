import datetime

from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class EventSeries(BaseK8sModel):
    """EventSeries contain information on series of events, i.e. thing that was/is happening continuously for some time."""

    count: int | None = Field(
        default=None,
        alias="count",
        description="Number of occurrences in this series up to the last heartbeat time",
    )
    last_observed_time: datetime.datetime | None = Field(
        default=None,
        alias="lastObservedTime",
        description="Time of the last occurrence observed",
    )
