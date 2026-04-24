from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import Field

from kubex.k8s.v1_34.core.v1.pod_spec import PodSpec
from kubex.k8s.v1_34.core.v1.pod_status import PodStatus
from kubex_core.models.interfaces import (
    Evictable,
    HasAttach,
    HasEphemeralContainers,
    HasExec,
    HasLogs,
    HasPortForward,
    HasResize,
    HasStatusSubresource,
    NamespaceScopedEntity,
)
from kubex_core.models.resource_config import ResourceConfig, Scope


class Pod(
    NamespaceScopedEntity,
    HasLogs,
    Evictable,
    HasStatusSubresource,
    HasEphemeralContainers,
    HasResize,
    HasAttach,
    HasExec,
    HasPortForward,
):
    """Pod is a collection of containers that can run on a host. This resource is created by clients and scheduled onto hosts."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["Pod"]] = ResourceConfig["Pod"](
        version="v1",
        kind="Pod",
        group="core",
        plural="pods",
        scope=Scope.NAMESPACE,
    )
    api_version: Literal["v1"] = Field(
        default="v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["Pod"] = Field(
        default="Pod",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: PodSpec | None = Field(
        default=None,
        alias="spec",
        description="Specification of the desired behavior of the pod. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#spec-and-status",
    )
    status: PodStatus | None = Field(
        default=None,
        alias="status",
        description="Most recently observed status of the pod. This data may not be up to date. Populated by the system. Read-only. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#spec-and-status",
    )
