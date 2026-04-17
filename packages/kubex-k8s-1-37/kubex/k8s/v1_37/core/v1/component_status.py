from __future__ import annotations

from typing import ClassVar, Literal

from kubex.k8s.v1_37.core.v1.component_condition import ComponentCondition
from kubex_core.models.interfaces import ClusterScopedEntity
from kubex_core.models.resource_config import ResourceConfig, Scope
from pydantic import Field


class ComponentStatus(ClusterScopedEntity):
    """ComponentStatus (and ComponentStatusList) holds the cluster validation info. Deprecated: This API is deprecated in v1.19+"""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["ComponentStatus"]] = ResourceConfig[
        "ComponentStatus"
    ](
        version="v1",
        kind="ComponentStatus",
        group="core",
        plural="componentstatuses",
        scope=Scope.CLUSTER,
    )
    api_version: Literal["v1"] = Field(
        default="v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    conditions: list[ComponentCondition] | None = Field(
        default=None,
        alias="conditions",
        description="List of component conditions observed",
    )
    kind: Literal["ComponentStatus"] = Field(
        default="ComponentStatus",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
