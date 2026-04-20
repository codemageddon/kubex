from __future__ import annotations

from typing import Literal

from pydantic import Field

from kubex.k8s.v1_34.resource.v1beta1.resource_slice import ResourceSlice
from kubex_core.models.list_entity import ListEntity
from kubex_core.models.metadata import ListMetadata


class ResourceSliceList(ListEntity[ResourceSlice]):
    """ResourceSliceList is a collection of ResourceSlices."""

    api_version: Literal["resource.k8s.io/v1beta1"] = Field(
        default="resource.k8s.io/v1beta1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    items: list[ResourceSlice] = Field(
        ..., alias="items", description="Items is the list of resource ResourceSlices."
    )
    kind: Literal["ResourceSliceList"] = Field(
        default="ResourceSliceList",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    metadata: ListMetadata = Field(
        ..., alias="metadata", description="Standard list metadata"
    )


ResourceSlice.__RESOURCE_CONFIG__._list_model = ResourceSliceList
