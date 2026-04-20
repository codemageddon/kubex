from __future__ import annotations

from typing import Literal

from pydantic import Field

from kubex.k8s.v1_34.autoscaling.v2.horizontal_pod_autoscaler import (
    HorizontalPodAutoscaler,
)
from kubex_core.models.list_entity import ListEntity
from kubex_core.models.metadata import ListMetadata


class HorizontalPodAutoscalerList(ListEntity[HorizontalPodAutoscaler]):
    """HorizontalPodAutoscalerList is a list of horizontal pod autoscaler objects."""

    api_version: Literal["autoscaling/v2"] = Field(
        default="autoscaling/v2",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    items: list[HorizontalPodAutoscaler] = Field(
        ...,
        alias="items",
        description="items is the list of horizontal pod autoscaler objects.",
    )
    kind: Literal["HorizontalPodAutoscalerList"] = Field(
        default="HorizontalPodAutoscalerList",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    metadata: ListMetadata = Field(
        ..., alias="metadata", description="metadata is the standard list metadata."
    )


HorizontalPodAutoscaler.__RESOURCE_CONFIG__._list_model = HorizontalPodAutoscalerList
