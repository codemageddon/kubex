from __future__ import annotations

from typing import ClassVar, Literal

from kubex_core.models.interfaces import NamespaceScopedEntity
from kubex_core.models.resource_config import ResourceConfig, Scope
from pydantic import Field


class ConfigMap(NamespaceScopedEntity):
    """ConfigMap holds configuration data for pods to consume."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["ConfigMap"]] = ResourceConfig[
        "ConfigMap"
    ](
        version="v1",
        kind="ConfigMap",
        group="core",
        plural="configmaps",
        scope=Scope.NAMESPACE,
    )
    api_version: Literal["v1"] = Field(
        default="v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    binary_data: dict[str, str] | None = Field(
        default=None,
        alias="binaryData",
        description="BinaryData contains the binary data. Each key must consist of alphanumeric characters, '-', '_' or '.'. BinaryData can contain byte sequences that are not in the UTF-8 range. The keys stored in BinaryData must not overlap with the ones in the Data field, this is enforced during validation process. Using this field will require 1.10+ apiserver and kubelet.",
    )
    data: dict[str, str] | None = Field(
        default=None,
        alias="data",
        description="Data contains the configuration data. Each key must consist of alphanumeric characters, '-', '_' or '.'. Values with non-UTF-8 byte sequences must use the BinaryData field. The keys stored in Data must not overlap with the keys in the BinaryData field, this is enforced during validation process.",
    )
    immutable: bool | None = Field(
        default=None,
        alias="immutable",
        description="Immutable, if set to true, ensures that data stored in the ConfigMap cannot be updated (only object metadata can be modified). If not set to true, the field can be modified at any time. Defaulted to nil.",
    )
    kind: Literal["ConfigMap"] = Field(
        default="ConfigMap",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
