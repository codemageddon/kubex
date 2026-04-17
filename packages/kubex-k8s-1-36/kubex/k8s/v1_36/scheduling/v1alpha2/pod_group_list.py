from __future__ import annotations

from typing import Literal

from kubex.k8s.v1_36.scheduling.v1alpha2.pod_group import PodGroup
from kubex_core.models.list_entity import ListEntity
from kubex_core.models.metadata import ListMetadata
from pydantic import Field


class PodGroupList(ListEntity[PodGroup]):
    """PodGroupList contains a list of PodGroup resources."""

    api_version: Literal["scheduling.k8s.io/v1alpha2"] = Field(
        default="scheduling.k8s.io/v1alpha2",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    items: list[PodGroup] = Field(
        ..., alias="items", description="Items is the list of PodGroups."
    )
    kind: Literal["PodGroupList"] = Field(
        default="PodGroupList",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    metadata: ListMetadata = Field(
        ..., alias="metadata", description="Standard list metadata."
    )


PodGroup.__RESOURCE_CONFIG__._list_model = PodGroupList
