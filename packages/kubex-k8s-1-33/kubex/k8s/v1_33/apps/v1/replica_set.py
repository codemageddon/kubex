from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import Field

from kubex.k8s.v1_33.apps.v1.replica_set_spec import ReplicaSetSpec
from kubex.k8s.v1_33.apps.v1.replica_set_status import ReplicaSetStatus
from kubex_core.models.interfaces import (
    HasScaleSubresource,
    HasStatusSubresource,
    NamespaceScopedEntity,
)
from kubex_core.models.resource_config import ResourceConfig, Scope


class ReplicaSet(NamespaceScopedEntity, HasScaleSubresource, HasStatusSubresource):
    """ReplicaSet ensures that a specified number of pod replicas are running at any given time."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["ReplicaSet"]] = ResourceConfig[
        "ReplicaSet"
    ](
        version="v1",
        kind="ReplicaSet",
        group="apps",
        plural="replicasets",
        scope=Scope.NAMESPACE,
    )
    api_version: Literal["apps/v1"] = Field(
        default="apps/v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["ReplicaSet"] = Field(
        default="ReplicaSet",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: ReplicaSetSpec | None = Field(
        default=None,
        alias="spec",
        description="Spec defines the specification of the desired behavior of the ReplicaSet. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#spec-and-status",
    )
    status: ReplicaSetStatus | None = Field(
        default=None,
        alias="status",
        description="Status is the most recently observed status of the ReplicaSet. This data may be out of date by some window of time. Populated by the system. Read-only. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#spec-and-status",
    )
