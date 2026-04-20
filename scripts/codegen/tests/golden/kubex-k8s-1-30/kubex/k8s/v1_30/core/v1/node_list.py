from __future__ import annotations

from typing import Literal

from pydantic import Field

from kubex.k8s.v1_30.core.v1.node import Node
from kubex_core.models.list_entity import ListEntity
from kubex_core.models.metadata import ListMetadata


class NodeList(ListEntity[Node]):
    """NodeList is the whole list of all Nodes."""

    api_version: Literal["v1"] = Field(default="v1", alias="apiVersion")
    items: list[Node] = Field(..., alias="items")
    kind: Literal["NodeList"] = Field(default="NodeList", alias="kind")
    metadata: ListMetadata = Field(..., alias="metadata")


Node.__RESOURCE_CONFIG__._list_model = NodeList
