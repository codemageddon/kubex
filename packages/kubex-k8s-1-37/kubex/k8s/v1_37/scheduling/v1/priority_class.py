from __future__ import annotations

from typing import ClassVar, Literal

from kubex_core.models.interfaces import ClusterScopedEntity
from kubex_core.models.resource_config import ResourceConfig, Scope
from pydantic import Field


class PriorityClass(ClusterScopedEntity):
    """PriorityClass defines mapping from a priority class name to the priority integer value. The value can be any valid integer."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["PriorityClass"]] = ResourceConfig[
        "PriorityClass"
    ](
        version="v1",
        kind="PriorityClass",
        group="scheduling.k8s.io",
        plural="priorityclasses",
        scope=Scope.CLUSTER,
    )
    api_version: Literal["scheduling.k8s.io/v1"] = Field(
        default="scheduling.k8s.io/v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    description: str | None = Field(
        default=None,
        alias="description",
        description="description is an arbitrary string that usually provides guidelines on when this priority class should be used.",
    )
    global_default: bool | None = Field(
        default=None,
        alias="globalDefault",
        description="globalDefault specifies whether this PriorityClass should be considered as the default priority for pods that do not have any priority class. Only one PriorityClass can be marked as `globalDefault`. However, if more than one PriorityClasses exists with their `globalDefault` field set to true, the smallest value of such global default PriorityClasses will be used as the default priority.",
    )
    kind: Literal["PriorityClass"] = Field(
        default="PriorityClass",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    preemption_policy: str | None = Field(
        default=None,
        alias="preemptionPolicy",
        description="preemptionPolicy is the Policy for preempting pods with lower priority. One of Never, PreemptLowerPriority. Defaults to PreemptLowerPriority if unset.",
    )
    value: int | None = Field(
        default=None,
        alias="value",
        description="value represents the integer value of this priority class. This is the actual priority that pods receive when they have the name of this class in their pod spec.",
    )
