from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class NodeAddress(BaseK8sModel):
    """NodeAddress reports a node address."""

    address: str = Field(..., alias="address")
    internal_ip: str | None = Field(default=None, alias="internalIP")
    pod_ips: list[str] | None = Field(default=None, alias="podIPs")
    some_nice_api: str | None = Field(default=None, alias="someNiceAPI")
    type_: str = Field(..., alias="type")
