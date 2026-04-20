from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import Field

from kubex.k8s.v1_32.apps.v1.daemon_set_spec import DaemonSetSpec
from kubex.k8s.v1_32.apps.v1.daemon_set_status import DaemonSetStatus
from kubex_core.models.interfaces import HasStatusSubresource, NamespaceScopedEntity
from kubex_core.models.resource_config import ResourceConfig, Scope


class DaemonSet(NamespaceScopedEntity, HasStatusSubresource):
    """DaemonSet represents the configuration of a daemon set."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["DaemonSet"]] = ResourceConfig[
        "DaemonSet"
    ](
        version="v1",
        kind="DaemonSet",
        group="apps",
        plural="daemonsets",
        scope=Scope.NAMESPACE,
    )
    api_version: Literal["apps/v1"] = Field(
        default="apps/v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["DaemonSet"] = Field(
        default="DaemonSet",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: DaemonSetSpec | None = Field(
        default=None,
        alias="spec",
        description="The desired behavior of this daemon set. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#spec-and-status",
    )
    status: DaemonSetStatus | None = Field(
        default=None,
        alias="status",
        description="The current status of this daemon set. This data may be out of date by some window of time. Populated by the system. Read-only. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#spec-and-status",
    )
