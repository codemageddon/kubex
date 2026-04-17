from __future__ import annotations

from typing import Literal

from kubex.k8s.v1_36.core.v1.resource_quota import ResourceQuota
from kubex_core.models.list_entity import ListEntity
from kubex_core.models.metadata import ListMetadata
from pydantic import Field


class ResourceQuotaList(ListEntity[ResourceQuota]):
    """ResourceQuotaList is a list of ResourceQuota items."""

    api_version: Literal["v1"] = Field(
        default="v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    items: list[ResourceQuota] = Field(
        ...,
        alias="items",
        description="Items is a list of ResourceQuota objects. More info: https://kubernetes.io/docs/concepts/policy/resource-quotas/",
    )
    kind: Literal["ResourceQuotaList"] = Field(
        default="ResourceQuotaList",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    metadata: ListMetadata = Field(
        ...,
        alias="metadata",
        description="Standard list metadata. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )


ResourceQuota.__RESOURCE_CONFIG__._list_model = ResourceQuotaList
