from __future__ import annotations

from typing import Literal

from pydantic import Field

from kubex.k8s.v1_32.rbac.v1.role import Role
from kubex_core.models.list_entity import ListEntity
from kubex_core.models.metadata import ListMetadata


class RoleList(ListEntity[Role]):
    """RoleList is a collection of Roles"""

    api_version: Literal["rbac.authorization.k8s.io/v1"] = Field(
        default="rbac.authorization.k8s.io/v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    items: list[Role] = Field(
        ..., alias="items", description="Items is a list of Roles"
    )
    kind: Literal["RoleList"] = Field(
        default="RoleList",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    metadata: ListMetadata = Field(
        ..., alias="metadata", description="Standard object's metadata."
    )


Role.__RESOURCE_CONFIG__._list_model = RoleList
