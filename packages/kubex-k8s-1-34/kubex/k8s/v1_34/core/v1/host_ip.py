from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class HostIP(BaseK8sModel):
    """HostIP represents a single IP address allocated to the host."""

    ip: str = Field(
        ..., alias="ip", description="IP is the IP address assigned to the host"
    )
