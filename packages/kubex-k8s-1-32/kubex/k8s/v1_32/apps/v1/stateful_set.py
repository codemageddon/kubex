from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import Field

from kubex.k8s.v1_32.apps.v1.stateful_set_spec import StatefulSetSpec
from kubex.k8s.v1_32.apps.v1.stateful_set_status import StatefulSetStatus
from kubex_core.models.interfaces import (
    HasScaleSubresource,
    HasStatusSubresource,
    NamespaceScopedEntity,
)
from kubex_core.models.resource_config import ResourceConfig, Scope


class StatefulSet(NamespaceScopedEntity, HasScaleSubresource, HasStatusSubresource):
    """StatefulSet represents a set of pods with consistent identities. Identities are defined as: - Network: A single stable DNS and hostname. - Storage: As many VolumeClaims as requested. The StatefulSet guarantees that a given network identity will always map to the same storage identity."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["StatefulSet"]] = ResourceConfig[
        "StatefulSet"
    ](
        version="v1",
        kind="StatefulSet",
        group="apps",
        plural="statefulsets",
        scope=Scope.NAMESPACE,
    )
    api_version: Literal["apps/v1"] = Field(
        default="apps/v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["StatefulSet"] = Field(
        default="StatefulSet",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: StatefulSetSpec | None = Field(
        default=None,
        alias="spec",
        description="Spec defines the desired identities of pods in this set.",
    )
    status: StatefulSetStatus | None = Field(
        default=None,
        alias="status",
        description="Status is the current status of Pods in this StatefulSet. This data may be out of date by some window of time.",
    )
