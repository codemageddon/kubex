from __future__ import annotations

from typing import Literal

from pydantic import Field

from kubex.k8s.v1_37.core.v1.namespace import Namespace
from kubex_core.models.list_entity import ListEntity
from kubex_core.models.metadata import ListMetadata


class NamespaceList(ListEntity[Namespace]):
    """NamespaceList is a list of Namespaces."""

    api_version: Literal["v1"] = Field(
        default="v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    items: list[Namespace] = Field(
        ...,
        alias="items",
        description="Items is the list of Namespace objects in the list. More info: https://kubernetes.io/docs/concepts/overview/working-with-objects/namespaces/",
    )
    kind: Literal["NamespaceList"] = Field(
        default="NamespaceList",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    metadata: ListMetadata = Field(
        ...,
        alias="metadata",
        description="Standard list metadata. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )


Namespace.__RESOURCE_CONFIG__._list_model = NamespaceList
