from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class ServiceCIDRSpec(BaseK8sModel):
    """ServiceCIDRSpec define the CIDRs the user wants to use for allocating ClusterIPs for Services."""

    cidrs: list[str] | None = Field(
        default=None,
        alias="cidrs",
        description='CIDRs defines the IP blocks in CIDR notation (e.g. "192.168.0.0/24" or "2001:db8::/64") from which to assign service cluster IPs. Max of two CIDRs is allowed, one of each IP family. This field is immutable.',
    )
