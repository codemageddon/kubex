from __future__ import annotations

from typing import Literal

from pydantic import Field

from kubex.k8s.v1_35.batch.v1.job import Job
from kubex_core.models.list_entity import ListEntity
from kubex_core.models.metadata import ListMetadata


class JobList(ListEntity[Job]):
    """JobList is a collection of jobs."""

    api_version: Literal["batch/v1"] = Field(
        default="batch/v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    items: list[Job] = Field(
        ..., alias="items", description="items is the list of Jobs."
    )
    kind: Literal["JobList"] = Field(
        default="JobList",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    metadata: ListMetadata = Field(
        ...,
        alias="metadata",
        description="Standard list metadata. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#metadata",
    )


Job.__RESOURCE_CONFIG__._list_model = JobList
