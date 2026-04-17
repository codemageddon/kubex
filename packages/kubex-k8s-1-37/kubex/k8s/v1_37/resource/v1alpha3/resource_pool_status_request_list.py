from __future__ import annotations

from typing import Literal

from kubex.k8s.v1_37.resource.v1alpha3.resource_pool_status_request import (
    ResourcePoolStatusRequest,
)
from kubex_core.models.list_entity import ListEntity
from kubex_core.models.metadata import ListMetadata
from pydantic import Field


class ResourcePoolStatusRequestList(ListEntity[ResourcePoolStatusRequest]):
    """ResourcePoolStatusRequestList is a collection of ResourcePoolStatusRequests."""

    api_version: Literal["resource.k8s.io/v1alpha3"] = Field(
        default="resource.k8s.io/v1alpha3",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    items: list[ResourcePoolStatusRequest] = Field(
        ...,
        alias="items",
        description="Items is the list of ResourcePoolStatusRequests.",
    )
    kind: Literal["ResourcePoolStatusRequestList"] = Field(
        default="ResourcePoolStatusRequestList",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    metadata: ListMetadata = Field(
        ..., alias="metadata", description="Standard list metadata"
    )


ResourcePoolStatusRequest.__RESOURCE_CONFIG__._list_model = (
    ResourcePoolStatusRequestList
)
