from pydantic import Field

from kubex.k8s.v1_32.core.v1.object_reference import ObjectReference
from kubex.k8s.v1_32.discovery.v1.endpoint_conditions import EndpointConditions
from kubex.k8s.v1_32.discovery.v1.endpoint_hints import EndpointHints
from kubex_core.models.base import BaseK8sModel


class Endpoint(BaseK8sModel):
    """Endpoint represents a single logical "backend" implementing a service."""

    addresses: list[str] = Field(
        ...,
        alias="addresses",
        description="addresses of this endpoint. The contents of this field are interpreted according to the corresponding EndpointSlice addressType field. Consumers must handle different types of addresses in the context of their own capabilities. This must contain at least one address but no more than 100. These are all assumed to be fungible and clients may choose to only use the first element. Refer to: https://issue.k8s.io/106267",
    )
    conditions: EndpointConditions | None = Field(
        default=None,
        alias="conditions",
        description="conditions contains information about the current status of the endpoint.",
    )
    deprecated_topology: dict[str, str] | None = Field(
        default=None,
        alias="deprecatedTopology",
        description="deprecatedTopology contains topology information part of the v1beta1 API. This field is deprecated, and will be removed when the v1beta1 API is removed (no sooner than kubernetes v1.24). While this field can hold values, it is not writable through the v1 API, and any attempts to write to it will be silently ignored. Topology information can be found in the zone and nodeName fields instead.",
    )
    hints: EndpointHints | None = Field(
        default=None,
        alias="hints",
        description="hints contains information associated with how an endpoint should be consumed.",
    )
    hostname: str | None = Field(
        default=None,
        alias="hostname",
        description="hostname of this endpoint. This field may be used by consumers of endpoints to distinguish endpoints from each other (e.g. in DNS names). Multiple endpoints which use the same hostname should be considered fungible (e.g. multiple A values in DNS). Must be lowercase and pass DNS Label (RFC 1123) validation.",
    )
    node_name: str | None = Field(
        default=None,
        alias="nodeName",
        description="nodeName represents the name of the Node hosting this endpoint. This can be used to determine endpoints local to a Node.",
    )
    target_ref: ObjectReference | None = Field(
        default=None,
        alias="targetRef",
        description="targetRef is a reference to a Kubernetes object that represents this endpoint.",
    )
    zone: str | None = Field(
        default=None,
        alias="zone",
        description="zone is the name of the Zone this endpoint exists in.",
    )
