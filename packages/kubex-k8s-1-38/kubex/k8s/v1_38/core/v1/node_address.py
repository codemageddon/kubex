from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class NodeAddress(BaseK8sModel):
    """NodeAddress contains information for the node's address."""

    address: str = Field(..., alias="address", description="The node address.")
    type_: str = Field(
        ...,
        alias="type",
        description="Node address type, one of Hostname, ExternalIP or InternalIP.",
    )
