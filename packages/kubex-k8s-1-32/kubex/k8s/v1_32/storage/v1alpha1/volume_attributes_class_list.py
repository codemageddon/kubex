from __future__ import annotations

from typing import Literal

from pydantic import Field

from kubex.k8s.v1_32.storage.v1alpha1.volume_attributes_class import (
    VolumeAttributesClass,
)
from kubex_core.models.list_entity import ListEntity
from kubex_core.models.metadata import ListMetadata


class VolumeAttributesClassList(ListEntity[VolumeAttributesClass]):
    """VolumeAttributesClassList is a collection of VolumeAttributesClass objects."""

    api_version: Literal["storage.k8s.io/v1alpha1"] = Field(
        default="storage.k8s.io/v1alpha1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    items: list[VolumeAttributesClass] = Field(
        ...,
        alias="items",
        description="items is the list of VolumeAttributesClass objects.",
    )
    kind: Literal["VolumeAttributesClassList"] = Field(
        default="VolumeAttributesClassList",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    metadata: ListMetadata = Field(
        ...,
        alias="metadata",
        description="Standard list metadata More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#metadata",
    )


VolumeAttributesClass.__RESOURCE_CONFIG__._list_model = VolumeAttributesClassList
