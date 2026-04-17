from __future__ import annotations

from typing import Literal

from kubex.k8s.v1_32.resource.v1beta1.device_class import DeviceClass
from kubex_core.models.list_entity import ListEntity
from kubex_core.models.metadata import ListMetadata
from pydantic import Field


class DeviceClassList(ListEntity[DeviceClass]):
    """DeviceClassList is a collection of classes."""

    api_version: Literal["resource.k8s.io/v1beta1"] = Field(
        default="resource.k8s.io/v1beta1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    items: list[DeviceClass] = Field(
        ..., alias="items", description="Items is the list of resource classes."
    )
    kind: Literal["DeviceClassList"] = Field(
        default="DeviceClassList",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    metadata: ListMetadata = Field(
        ..., alias="metadata", description="Standard list metadata"
    )


DeviceClass.__RESOURCE_CONFIG__._list_model = DeviceClassList
