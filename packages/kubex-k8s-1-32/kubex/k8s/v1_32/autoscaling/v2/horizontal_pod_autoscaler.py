from __future__ import annotations

from typing import ClassVar, Literal

from kubex.k8s.v1_32.autoscaling.v2.horizontal_pod_autoscaler_spec import (
    HorizontalPodAutoscalerSpec,
)
from kubex.k8s.v1_32.autoscaling.v2.horizontal_pod_autoscaler_status import (
    HorizontalPodAutoscalerStatus,
)
from kubex_core.models.interfaces import HasStatusSubresource, NamespaceScopedEntity
from kubex_core.models.resource_config import ResourceConfig, Scope
from pydantic import Field


class HorizontalPodAutoscaler(NamespaceScopedEntity, HasStatusSubresource):
    """HorizontalPodAutoscaler is the configuration for a horizontal pod autoscaler, which automatically manages the replica count of any resource implementing the scale subresource based on the metrics specified."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["HorizontalPodAutoscaler"]] = (
        ResourceConfig["HorizontalPodAutoscaler"](
            version="v2",
            kind="HorizontalPodAutoscaler",
            group="autoscaling",
            plural="horizontalpodautoscalers",
            scope=Scope.NAMESPACE,
        )
    )
    api_version: Literal["autoscaling/v2"] = Field(
        default="autoscaling/v2",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["HorizontalPodAutoscaler"] = Field(
        default="HorizontalPodAutoscaler",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: HorizontalPodAutoscalerSpec | None = Field(
        default=None,
        alias="spec",
        description="spec is the specification for the behaviour of the autoscaler. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#spec-and-status.",
    )
    status: HorizontalPodAutoscalerStatus | None = Field(
        default=None,
        alias="status",
        description="status is the current information about the autoscaler.",
    )
