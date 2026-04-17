from __future__ import annotations

from typing import ClassVar, Literal

from kubex.k8s.v1_35.core.v1.limit_range_spec import LimitRangeSpec
from kubex_core.models.interfaces import NamespaceScopedEntity
from kubex_core.models.resource_config import ResourceConfig, Scope
from pydantic import Field


class LimitRange(NamespaceScopedEntity):
    """LimitRange sets resource usage limits for each kind of resource in a Namespace."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["LimitRange"]] = ResourceConfig[
        "LimitRange"
    ](
        version="v1",
        kind="LimitRange",
        group="core",
        plural="limitranges",
        scope=Scope.NAMESPACE,
    )
    api_version: Literal["v1"] = Field(
        default="v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["LimitRange"] = Field(
        default="LimitRange",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: LimitRangeSpec | None = Field(
        default=None,
        alias="spec",
        description="Spec defines the limits enforced. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#spec-and-status",
    )
