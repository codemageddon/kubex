from __future__ import annotations

from typing import Literal

from kubex.k8s.v1_36.core.v1.node import Node
from kubex_core.models.list_entity import ListEntity
from kubex_core.models.metadata import ListMetadata
from pydantic import Field


class NodeList(ListEntity[Node]):
    """NodeList is the whole list of all Nodes which have been registered with master."""

    api_version: Literal["v1"] = Field(
        default="v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    items: list[Node] = Field(..., alias="items", description="List of nodes")
    kind: Literal["NodeList"] = Field(
        default="NodeList",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    metadata: ListMetadata = Field(
        ...,
        alias="metadata",
        description="Standard list metadata. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )


Node.__RESOURCE_CONFIG__._list_model = NodeList
