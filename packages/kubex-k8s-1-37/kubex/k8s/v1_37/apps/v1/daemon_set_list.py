from __future__ import annotations

from typing import Literal

from pydantic import Field

from kubex.k8s.v1_37.apps.v1.daemon_set import DaemonSet
from kubex_core.models.list_entity import ListEntity
from kubex_core.models.metadata import ListMetadata


class DaemonSetList(ListEntity[DaemonSet]):
    """DaemonSetList is a collection of daemon sets."""

    api_version: Literal["apps/v1"] = Field(
        default="apps/v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    items: list[DaemonSet] = Field(
        ..., alias="items", description="A list of daemon sets."
    )
    kind: Literal["DaemonSetList"] = Field(
        default="DaemonSetList",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    metadata: ListMetadata = Field(
        ...,
        alias="metadata",
        description="Standard list metadata. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#metadata",
    )


DaemonSet.__RESOURCE_CONFIG__._list_model = DaemonSetList
