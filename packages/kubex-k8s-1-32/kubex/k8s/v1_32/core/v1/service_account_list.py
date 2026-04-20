from __future__ import annotations

from typing import Literal

from pydantic import Field

from kubex.k8s.v1_32.core.v1.service_account import ServiceAccount
from kubex_core.models.list_entity import ListEntity
from kubex_core.models.metadata import ListMetadata


class ServiceAccountList(ListEntity[ServiceAccount]):
    """ServiceAccountList is a list of ServiceAccount objects"""

    api_version: Literal["v1"] = Field(
        default="v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    items: list[ServiceAccount] = Field(
        ...,
        alias="items",
        description="List of ServiceAccounts. More info: https://kubernetes.io/docs/tasks/configure-pod-container/configure-service-account/",
    )
    kind: Literal["ServiceAccountList"] = Field(
        default="ServiceAccountList",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    metadata: ListMetadata = Field(
        ...,
        alias="metadata",
        description="Standard list metadata. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )


ServiceAccount.__RESOURCE_CONFIG__._list_model = ServiceAccountList
