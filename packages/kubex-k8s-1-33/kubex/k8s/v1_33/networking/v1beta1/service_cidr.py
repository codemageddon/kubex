from __future__ import annotations

from typing import ClassVar, Literal

from kubex.k8s.v1_33.networking.v1beta1.service_cidr_spec import ServiceCIDRSpec
from kubex.k8s.v1_33.networking.v1beta1.service_cidr_status import ServiceCIDRStatus
from kubex_core.models.interfaces import ClusterScopedEntity, HasStatusSubresource
from kubex_core.models.resource_config import ResourceConfig, Scope
from pydantic import Field


class ServiceCIDR(ClusterScopedEntity, HasStatusSubresource):
    """ServiceCIDR defines a range of IP addresses using CIDR format (e.g. 192.168.0.0/24 or 2001:db2::/64). This range is used to allocate ClusterIPs to Service objects."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["ServiceCIDR"]] = ResourceConfig[
        "ServiceCIDR"
    ](
        version="v1beta1",
        kind="ServiceCIDR",
        group="networking.k8s.io",
        plural="servicecidrs",
        scope=Scope.CLUSTER,
    )
    api_version: Literal["networking.k8s.io/v1beta1"] = Field(
        default="networking.k8s.io/v1beta1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["ServiceCIDR"] = Field(
        default="ServiceCIDR",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: ServiceCIDRSpec | None = Field(
        default=None,
        alias="spec",
        description="spec is the desired state of the ServiceCIDR. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#spec-and-status",
    )
    status: ServiceCIDRStatus | None = Field(
        default=None,
        alias="status",
        description="status represents the current state of the ServiceCIDR. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#spec-and-status",
    )
