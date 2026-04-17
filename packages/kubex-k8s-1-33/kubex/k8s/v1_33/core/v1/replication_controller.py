from __future__ import annotations

from typing import ClassVar, Literal

from kubex.k8s.v1_33.core.v1.replication_controller_spec import (
    ReplicationControllerSpec,
)
from kubex.k8s.v1_33.core.v1.replication_controller_status import (
    ReplicationControllerStatus,
)
from kubex_core.models.interfaces import (
    HasScaleSubresource,
    HasStatusSubresource,
    NamespaceScopedEntity,
)
from kubex_core.models.resource_config import ResourceConfig, Scope
from pydantic import Field


class ReplicationController(
    NamespaceScopedEntity, HasScaleSubresource, HasStatusSubresource
):
    """ReplicationController represents the configuration of a replication controller."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["ReplicationController"]] = (
        ResourceConfig["ReplicationController"](
            version="v1",
            kind="ReplicationController",
            group="core",
            plural="replicationcontrollers",
            scope=Scope.NAMESPACE,
        )
    )
    api_version: Literal["v1"] = Field(
        default="v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["ReplicationController"] = Field(
        default="ReplicationController",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: ReplicationControllerSpec | None = Field(
        default=None,
        alias="spec",
        description="Spec defines the specification of the desired behavior of the replication controller. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#spec-and-status",
    )
    status: ReplicationControllerStatus | None = Field(
        default=None,
        alias="status",
        description="Status is the most recently observed status of the replication controller. This data may be out of date by some window of time. Populated by the system. Read-only. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#spec-and-status",
    )
