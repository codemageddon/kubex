from __future__ import annotations

from typing import Literal

from pydantic import Field

from kubex.k8s.v1_35.batch.v1.cron_job import CronJob
from kubex_core.models.list_entity import ListEntity
from kubex_core.models.metadata import ListMetadata


class CronJobList(ListEntity[CronJob]):
    """CronJobList is a collection of cron jobs."""

    api_version: Literal["batch/v1"] = Field(
        default="batch/v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    items: list[CronJob] = Field(
        ..., alias="items", description="items is the list of CronJobs."
    )
    kind: Literal["CronJobList"] = Field(
        default="CronJobList",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    metadata: ListMetadata = Field(
        ...,
        alias="metadata",
        description="Standard list metadata. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#metadata",
    )


CronJob.__RESOURCE_CONFIG__._list_model = CronJobList
