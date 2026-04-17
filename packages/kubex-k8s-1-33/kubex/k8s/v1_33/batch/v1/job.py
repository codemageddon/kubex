from __future__ import annotations

from typing import ClassVar, Literal

from kubex.k8s.v1_33.batch.v1.job_spec import JobSpec
from kubex.k8s.v1_33.batch.v1.job_status import JobStatus
from kubex_core.models.interfaces import HasStatusSubresource, NamespaceScopedEntity
from kubex_core.models.resource_config import ResourceConfig, Scope
from pydantic import Field


class Job(NamespaceScopedEntity, HasStatusSubresource):
    """Job represents the configuration of a single job."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["Job"]] = ResourceConfig["Job"](
        version="v1",
        kind="Job",
        group="batch",
        plural="jobs",
        scope=Scope.NAMESPACE,
    )
    api_version: Literal["batch/v1"] = Field(
        default="batch/v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["Job"] = Field(
        default="Job",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: JobSpec | None = Field(
        default=None,
        alias="spec",
        description="Specification of the desired behavior of a job. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#spec-and-status",
    )
    status: JobStatus | None = Field(
        default=None,
        alias="status",
        description="Current status of a job. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#spec-and-status",
    )
