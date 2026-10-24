from pydantic import Field

from kubex_core.models.base import BaseK8sModel
from kubex_core.models.types import MicroTime


class EventSeries(BaseK8sModel):
    """EventSeries contain information on series of events, i.e. thing that was/is happening continuously for some time."""

    count: int | None = Field(
        default=None,
        alias="count",
        description="count is the number of occurrences in this series up to the last heartbeat time",
    )
    last_observed_time: MicroTime | None = Field(
        default=None,
        alias="lastObservedTime",
        description="lastObservedTime is the time of the last occurrence observed",
    )
