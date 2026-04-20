from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class ResourcePoolStatusRequestSpec(BaseK8sModel):
    """ResourcePoolStatusRequestSpec defines the filters for the pool status request."""

    driver: str = Field(
        ...,
        alias="driver",
        description='Driver specifies the DRA driver name to filter pools. Only pools from ResourceSlices with this driver will be included. Must be a DNS subdomain (e.g., "gpu.example.com").',
    )
    limit: int | None = Field(
        default=None,
        alias="limit",
        description="Limit optionally specifies the maximum number of pools to return in the status. If more pools match the filter criteria, the response will be truncated (i.e., len(status.pools) < status.poolCount). Default: 100 Minimum: 1 Maximum: 1000",
    )
    pool_name: str | None = Field(
        default=None,
        alias="poolName",
        description='PoolName optionally filters to a specific pool name. If not specified, all pools from the specified driver are included. When specified, must be a non-empty valid resource pool name (DNS subdomains separated by "/").',
    )
