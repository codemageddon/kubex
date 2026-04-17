from __future__ import annotations

from typing import ClassVar, Literal

from kubex.k8s.v1_32.discovery.v1.endpoint import Endpoint
from kubex.k8s.v1_32.discovery.v1.endpoint_port import EndpointPort
from kubex_core.models.interfaces import ClusterScopedEntity
from kubex_core.models.resource_config import ResourceConfig, Scope
from pydantic import Field


class EndpointSlice(ClusterScopedEntity):
    """EndpointSlice represents a subset of the endpoints that implement a service. For a given service there may be multiple EndpointSlice objects, selected by labels, which must be joined to produce the full set of endpoints."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["EndpointSlice"]] = ResourceConfig[
        "EndpointSlice"
    ](
        version="v1",
        kind="EndpointSlice",
        group="discovery.k8s.io",
        plural="endpointslices",
        scope=Scope.CLUSTER,
    )
    address_type: str = Field(
        ...,
        alias="addressType",
        description="addressType specifies the type of address carried by this EndpointSlice. All addresses in this slice must be the same type. This field is immutable after creation. The following address types are currently supported: * IPv4: Represents an IPv4 Address. * IPv6: Represents an IPv6 Address. * FQDN: Represents a Fully Qualified Domain Name.",
    )
    api_version: Literal["discovery.k8s.io/v1"] = Field(
        default="discovery.k8s.io/v1",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    endpoints: list[Endpoint] = Field(
        ...,
        alias="endpoints",
        description="endpoints is a list of unique endpoints in this slice. Each slice may include a maximum of 1000 endpoints.",
    )
    kind: Literal["EndpointSlice"] = Field(
        default="EndpointSlice",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    ports: list[EndpointPort] | None = Field(
        default=None,
        alias="ports",
        description='ports specifies the list of network ports exposed by each endpoint in this slice. Each port must have a unique name. When ports is empty, it indicates that there are no defined ports. When a port is defined with a nil port value, it indicates "all ports". Each slice may include a maximum of 100 ports.',
    )
