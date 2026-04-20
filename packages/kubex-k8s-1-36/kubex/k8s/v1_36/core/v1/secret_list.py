from __future__ import annotations

from typing import Literal

from pydantic import Field

from kubex.k8s.v1_36.core.v1.secret import Secret
from kubex_core.models.list_entity import ListEntity
from kubex_core.models.metadata import ListMetadata


class SecretList(ListEntity[Secret]):
    """SecretList is a list of Secret."""

    api_version: Literal["v1"] = Field(
        default="v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    items: list[Secret] = Field(
        ...,
        alias="items",
        description="Items is a list of secret objects. More info: https://kubernetes.io/docs/concepts/configuration/secret",
    )
    kind: Literal["SecretList"] = Field(
        default="SecretList",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    metadata: ListMetadata = Field(
        ...,
        alias="metadata",
        description="Standard list metadata. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )


Secret.__RESOURCE_CONFIG__._list_model = SecretList
