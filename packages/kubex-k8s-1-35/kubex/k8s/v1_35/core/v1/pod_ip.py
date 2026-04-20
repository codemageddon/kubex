from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class PodIP(BaseK8sModel):
    """PodIP represents a single IP address allocated to the pod."""

    ip: str = Field(
        ..., alias="ip", description="IP is the IP address assigned to the pod"
    )
