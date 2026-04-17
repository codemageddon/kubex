from kubex.k8s.v1_35.discovery.v1.for_node import ForNode
from kubex.k8s.v1_35.discovery.v1.for_zone import ForZone
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class EndpointHints(BaseK8sModel):
    """EndpointHints provides hints describing how an endpoint should be consumed."""

    for_nodes: list[ForNode] | None = Field(
        default=None,
        alias="forNodes",
        description="forNodes indicates the node(s) this endpoint should be consumed by when using topology aware routing. May contain a maximum of 8 entries.",
    )
    for_zones: list[ForZone] | None = Field(
        default=None,
        alias="forZones",
        description="forZones indicates the zone(s) this endpoint should be consumed by when using topology aware routing. May contain a maximum of 8 entries.",
    )
