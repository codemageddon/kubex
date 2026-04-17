import datetime

from kubex.k8s.v1_32.core.v1.object_reference import ObjectReference
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class CronJobStatus(BaseK8sModel):
    """CronJobStatus represents the current state of a cron job."""

    active: list[ObjectReference] | None = Field(
        default=None,
        alias="active",
        description="A list of pointers to currently running jobs.",
    )
    last_schedule_time: datetime.datetime | None = Field(
        default=None,
        alias="lastScheduleTime",
        description="Information when was the last time the job was successfully scheduled.",
    )
    last_successful_time: datetime.datetime | None = Field(
        default=None,
        alias="lastSuccessfulTime",
        description="Information when was the last time the job successfully completed.",
    )
