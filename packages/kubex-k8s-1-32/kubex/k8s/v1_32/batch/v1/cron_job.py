from __future__ import annotations

from typing import ClassVar, Literal

from kubex.k8s.v1_32.batch.v1.cron_job_spec import CronJobSpec
from kubex.k8s.v1_32.batch.v1.cron_job_status import CronJobStatus
from kubex_core.models.interfaces import ClusterScopedEntity, HasStatusSubresource
from kubex_core.models.resource_config import ResourceConfig, Scope
from pydantic import Field


class CronJob(ClusterScopedEntity, HasStatusSubresource):
    """CronJob represents the configuration of a single cron job."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["CronJob"]] = ResourceConfig[
        "CronJob"
    ](
        version="v1",
        kind="CronJob",
        group="batch",
        plural="cronjobs",
        scope=Scope.CLUSTER,
    )
    api_version: Literal["batch/v1"] = Field(
        default="batch/v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["CronJob"] = Field(
        default="CronJob",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: CronJobSpec | None = Field(
        default=None,
        alias="spec",
        description="Specification of the desired behavior of a cron job, including the schedule. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#spec-and-status",
    )
    status: CronJobStatus | None = Field(
        default=None,
        alias="status",
        description="Current status of a cron job. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#spec-and-status",
    )
