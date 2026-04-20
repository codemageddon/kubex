from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import Field

from kubex.k8s.v1_33.flowcontrol.v1.priority_level_configuration_spec import (
    PriorityLevelConfigurationSpec,
)
from kubex.k8s.v1_33.flowcontrol.v1.priority_level_configuration_status import (
    PriorityLevelConfigurationStatus,
)
from kubex_core.models.interfaces import ClusterScopedEntity, HasStatusSubresource
from kubex_core.models.resource_config import ResourceConfig, Scope


class PriorityLevelConfiguration(ClusterScopedEntity, HasStatusSubresource):
    """PriorityLevelConfiguration represents the configuration of a priority level."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["PriorityLevelConfiguration"]] = (
        ResourceConfig["PriorityLevelConfiguration"](
            version="v1",
            kind="PriorityLevelConfiguration",
            group="flowcontrol.apiserver.k8s.io",
            plural="prioritylevelconfigurations",
            scope=Scope.CLUSTER,
        )
    )
    api_version: Literal["flowcontrol.apiserver.k8s.io/v1"] = Field(
        default="flowcontrol.apiserver.k8s.io/v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["PriorityLevelConfiguration"] = Field(
        default="PriorityLevelConfiguration",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: PriorityLevelConfigurationSpec | None = Field(
        default=None,
        alias="spec",
        description='`spec` is the specification of the desired behavior of a "request-priority". More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#spec-and-status',
    )
    status: PriorityLevelConfigurationStatus | None = Field(
        default=None,
        alias="status",
        description='`status` is the current status of a "request-priority". More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#spec-and-status',
    )
