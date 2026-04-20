from __future__ import annotations

from typing import Literal

from pydantic import Field

from kubex.k8s.v1_37.apiextensions_k8s_io.v1.custom_resource_definition import (
    CustomResourceDefinition,
)
from kubex_core.models.list_entity import ListEntity
from kubex_core.models.metadata import ListMetadata


class CustomResourceDefinitionList(ListEntity[CustomResourceDefinition]):
    """CustomResourceDefinitionList is a list of CustomResourceDefinition objects."""

    api_version: Literal["apiextensions.k8s.io/v1"] = Field(
        default="apiextensions.k8s.io/v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    items: list[CustomResourceDefinition] = Field(
        ...,
        alias="items",
        description="items list individual CustomResourceDefinition objects",
    )
    kind: Literal["CustomResourceDefinitionList"] = Field(
        default="CustomResourceDefinitionList",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    metadata: ListMetadata = Field(
        ...,
        alias="metadata",
        description="Standard object's metadata More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#metadata",
    )


CustomResourceDefinition.__RESOURCE_CONFIG__._list_model = CustomResourceDefinitionList
