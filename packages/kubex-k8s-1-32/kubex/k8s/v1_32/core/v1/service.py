from __future__ import annotations

from typing import ClassVar, Literal

from kubex.k8s.v1_32.core.v1.service_spec import ServiceSpec
from kubex.k8s.v1_32.core.v1.service_status import ServiceStatus
from kubex_core.models.interfaces import HasStatusSubresource, NamespaceScopedEntity
from kubex_core.models.resource_config import ResourceConfig, Scope
from pydantic import Field


class Service(NamespaceScopedEntity, HasStatusSubresource):
    """Service is a named abstraction of software service (for example, mysql) consisting of local port (for example 3306) that the proxy listens on, and the selector that determines which pods will answer requests sent through the proxy."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["Service"]] = ResourceConfig[
        "Service"
    ](
        version="v1",
        kind="Service",
        group="core",
        plural="services",
        scope=Scope.NAMESPACE,
    )
    api_version: Literal["v1"] = Field(
        default="v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["Service"] = Field(
        default="Service",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: ServiceSpec | None = Field(
        default=None,
        alias="spec",
        description="Spec defines the behavior of a service. https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#spec-and-status",
    )
    status: ServiceStatus | None = Field(
        default=None,
        alias="status",
        description="Most recently observed status of the service. Populated by the system. Read-only. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#spec-and-status",
    )
