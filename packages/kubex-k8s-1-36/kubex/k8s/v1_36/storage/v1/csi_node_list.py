from __future__ import annotations

from typing import Literal

from kubex.k8s.v1_36.storage.v1.csi_node import CSINode
from kubex_core.models.list_entity import ListEntity
from kubex_core.models.metadata import ListMetadata
from pydantic import Field


class CSINodeList(ListEntity[CSINode]):
    """CSINodeList is a collection of CSINode objects."""

    api_version: Literal["storage.k8s.io/v1"] = Field(
        default="storage.k8s.io/v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    items: list[CSINode] = Field(
        ..., alias="items", description="items is the list of CSINode"
    )
    kind: Literal["CSINodeList"] = Field(
        default="CSINodeList",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    metadata: ListMetadata = Field(
        ...,
        alias="metadata",
        description="Standard list metadata More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#metadata",
    )


CSINode.__RESOURCE_CONFIG__._list_model = CSINodeList
