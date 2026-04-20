from __future__ import annotations

from typing import Literal

from pydantic import Field

from kubex.k8s.v1_34.core.v1.endpoints import Endpoints
from kubex_core.models.list_entity import ListEntity
from kubex_core.models.metadata import ListMetadata


class EndpointsList(ListEntity[Endpoints]):
    """EndpointsList is a list of endpoints. Deprecated: This API is deprecated in v1.33+."""

    api_version: Literal["v1"] = Field(
        default="v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    items: list[Endpoints] = Field(..., alias="items", description="List of endpoints.")
    kind: Literal["EndpointsList"] = Field(
        default="EndpointsList",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    metadata: ListMetadata = Field(
        ...,
        alias="metadata",
        description="Standard list metadata. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )


Endpoints.__RESOURCE_CONFIG__._list_model = EndpointsList
