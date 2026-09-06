from __future__ import annotations

from typing import Literal

from pydantic import Field

from kubex.k8s.v1_37.lifecycle.v1alpha1.eviction import Eviction
from kubex_core.models.list_entity import ListEntity
from kubex_core.models.metadata import ListMetadata


class EvictionList(ListEntity[Eviction]):
    """EvictionList contains a list of Eviction resources."""

    api_version: Literal["lifecycle.k8s.io/v1alpha1"] = Field(
        default="lifecycle.k8s.io/v1alpha1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    items: list[Eviction] = Field(
        ..., alias="items", description="items is the list of Evictions."
    )
    kind: Literal["EvictionList"] = Field(
        default="EvictionList",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    metadata: ListMetadata = Field(
        ...,
        alias="metadata",
        description="metadata is the standard list metadata. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#metadata",
    )


Eviction.__RESOURCE_CONFIG__._list_model = EvictionList
