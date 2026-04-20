from __future__ import annotations

from typing import Literal

from pydantic import Field

from kubex.k8s.v1_36.resource.v1.resource_claim import ResourceClaim
from kubex_core.models.list_entity import ListEntity
from kubex_core.models.metadata import ListMetadata


class ResourceClaimList(ListEntity[ResourceClaim]):
    """ResourceClaimList is a collection of claims."""

    api_version: Literal["resource.k8s.io/v1"] = Field(
        default="resource.k8s.io/v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    items: list[ResourceClaim] = Field(
        ..., alias="items", description="Items is the list of resource claims."
    )
    kind: Literal["ResourceClaimList"] = Field(
        default="ResourceClaimList",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    metadata: ListMetadata = Field(
        ..., alias="metadata", description="Standard list metadata"
    )


ResourceClaim.__RESOURCE_CONFIG__._list_model = ResourceClaimList
