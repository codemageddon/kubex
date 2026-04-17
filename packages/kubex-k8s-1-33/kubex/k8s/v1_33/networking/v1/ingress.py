from __future__ import annotations

from typing import ClassVar, Literal

from kubex.k8s.v1_33.networking.v1.ingress_spec import IngressSpec
from kubex.k8s.v1_33.networking.v1.ingress_status import IngressStatus
from kubex_core.models.interfaces import HasStatusSubresource, NamespaceScopedEntity
from kubex_core.models.resource_config import ResourceConfig, Scope
from pydantic import Field


class Ingress(NamespaceScopedEntity, HasStatusSubresource):
    """Ingress is a collection of rules that allow inbound connections to reach the endpoints defined by a backend. An Ingress can be configured to give services externally-reachable urls, load balance traffic, terminate SSL, offer name based virtual hosting etc."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["Ingress"]] = ResourceConfig[
        "Ingress"
    ](
        version="v1",
        kind="Ingress",
        group="networking.k8s.io",
        plural="ingresses",
        scope=Scope.NAMESPACE,
    )
    api_version: Literal["networking.k8s.io/v1"] = Field(
        default="networking.k8s.io/v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["Ingress"] = Field(
        default="Ingress",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: IngressSpec | None = Field(
        default=None,
        alias="spec",
        description="spec is the desired state of the Ingress. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#spec-and-status",
    )
    status: IngressStatus | None = Field(
        default=None,
        alias="status",
        description="status is the current state of the Ingress. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#spec-and-status",
    )
