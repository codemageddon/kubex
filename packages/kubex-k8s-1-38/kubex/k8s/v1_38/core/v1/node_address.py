from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class NodeAddress(BaseK8sModel):
    """NodeAddress contains information for the node's address."""

    address: str = Field(
        ..., alias="address", description="address is the node address."
    )
    type_: str = Field(
        ...,
        alias="type",
        description="type is the node address type, one of Hostname, ExternalIP or InternalIP.",
    )
