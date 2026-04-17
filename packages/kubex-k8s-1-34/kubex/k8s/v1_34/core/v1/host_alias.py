from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class HostAlias(BaseK8sModel):
    """HostAlias holds the mapping between IP and hostnames that will be injected as an entry in the pod's hosts file."""

    hostnames: list[str] | None = Field(
        default=None,
        alias="hostnames",
        description="Hostnames for the above IP address.",
    )
    ip: str = Field(..., alias="ip", description="IP address of the host file entry.")
