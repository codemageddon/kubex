from pydantic import Field

from kubex.k8s.v1_32.discovery.v1.for_zone import ForZone
from kubex_core.models.base import BaseK8sModel


class EndpointHints(BaseK8sModel):
    """EndpointHints provides hints describing how an endpoint should be consumed."""

    for_zones: list[ForZone] | None = Field(
        default=None,
        alias="forZones",
        description="forZones indicates the zone(s) this endpoint should be consumed by to enable topology aware routing.",
    )
