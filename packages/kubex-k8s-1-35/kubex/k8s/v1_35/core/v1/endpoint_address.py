from pydantic import Field

from kubex.k8s.v1_35.core.v1.object_reference import ObjectReference
from kubex_core.models.base import BaseK8sModel


class EndpointAddress(BaseK8sModel):
    """EndpointAddress is a tuple that describes single IP address. Deprecated: This API is deprecated in v1.33+."""

    hostname: str | None = Field(
        default=None, alias="hostname", description="The Hostname of this endpoint"
    )
    ip: str = Field(
        ...,
        alias="ip",
        description="The IP of this endpoint. May not be loopback (127.0.0.0/8 or ::1), link-local (169.254.0.0/16 or fe80::/10), or link-local multicast (224.0.0.0/24 or ff02::/16).",
    )
    node_name: str | None = Field(
        default=None,
        alias="nodeName",
        description="Optional: Node hosting this endpoint. This can be used to determine endpoints local to a node.",
    )
    target_ref: ObjectReference | None = Field(
        default=None,
        alias="targetRef",
        description="Reference to object providing the endpoint.",
    )
