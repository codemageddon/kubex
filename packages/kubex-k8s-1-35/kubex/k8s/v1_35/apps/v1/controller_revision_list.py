from __future__ import annotations

from typing import Literal

from pydantic import Field

from kubex.k8s.v1_35.apps.v1.controller_revision import ControllerRevision
from kubex_core.models.list_entity import ListEntity
from kubex_core.models.metadata import ListMetadata


class ControllerRevisionList(ListEntity[ControllerRevision]):
    """ControllerRevisionList is a resource containing a list of ControllerRevision objects."""

    api_version: Literal["apps/v1"] = Field(
        default="apps/v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    items: list[ControllerRevision] = Field(
        ..., alias="items", description="Items is the list of ControllerRevisions"
    )
    kind: Literal["ControllerRevisionList"] = Field(
        default="ControllerRevisionList",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    metadata: ListMetadata = Field(
        ...,
        alias="metadata",
        description="More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#metadata",
    )


ControllerRevision.__RESOURCE_CONFIG__._list_model = ControllerRevisionList
