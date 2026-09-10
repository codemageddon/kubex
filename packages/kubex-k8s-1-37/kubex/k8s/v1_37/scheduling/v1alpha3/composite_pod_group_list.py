from __future__ import annotations

from typing import Literal

from pydantic import Field

from kubex.k8s.v1_37.scheduling.v1alpha3.composite_pod_group import CompositePodGroup
from kubex_core.models.list_entity import ListEntity
from kubex_core.models.metadata import ListMetadata


class CompositePodGroupList(ListEntity[CompositePodGroup]):
    """CompositePodGroupList contains a list of CompositePodGroup resources."""

    api_version: Literal["scheduling.k8s.io/v1alpha3"] = Field(
        default="scheduling.k8s.io/v1alpha3",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    items: list[CompositePodGroup] = Field(
        ..., alias="items", description="Items is the list of CompositePodGroups."
    )
    kind: Literal["CompositePodGroupList"] = Field(
        default="CompositePodGroupList",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    metadata: ListMetadata = Field(
        ..., alias="metadata", description="Standard list metadata."
    )


CompositePodGroup.__RESOURCE_CONFIG__._list_model = CompositePodGroupList
