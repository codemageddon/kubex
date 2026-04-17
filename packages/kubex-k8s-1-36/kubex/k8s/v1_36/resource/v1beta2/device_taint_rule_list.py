from __future__ import annotations

from typing import Literal

from kubex.k8s.v1_36.resource.v1beta2.device_taint_rule import DeviceTaintRule
from kubex_core.models.list_entity import ListEntity
from kubex_core.models.metadata import ListMetadata
from pydantic import Field


class DeviceTaintRuleList(ListEntity[DeviceTaintRule]):
    """DeviceTaintRuleList is a collection of DeviceTaintRules."""

    api_version: Literal["resource.k8s.io/v1beta2"] = Field(
        default="resource.k8s.io/v1beta2",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    items: list[DeviceTaintRule] = Field(
        ..., alias="items", description="Items is the list of DeviceTaintRules."
    )
    kind: Literal["DeviceTaintRuleList"] = Field(
        default="DeviceTaintRuleList",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    metadata: ListMetadata = Field(
        ..., alias="metadata", description="Standard list metadata"
    )


DeviceTaintRule.__RESOURCE_CONFIG__._list_model = DeviceTaintRuleList
