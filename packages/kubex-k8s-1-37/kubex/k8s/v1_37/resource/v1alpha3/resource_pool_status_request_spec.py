from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class ResourcePoolStatusRequestSpec(BaseK8sModel):
    """ResourcePoolStatusRequestSpec defines the filters for the pool status request."""

    default_partition_type_attribute: str | None = Field(
        default=None,
        alias="defaultPartitionTypeAttribute",
        description='DefaultPartitionTypeAttribute optionally names a device attribute (by its fully qualified name, e.g. "gpu.example.com/profile") to use as the default grouping attribute for partitionable devices whose slice has not declared one themselves. A slice\'s own PartitionTypeAttribute always takes precedence. This default applies only to devices whose slice does not declare one, so that a request can still get an accurate partitionSummary from a driver that has not been updated to declare it. When neither the slice nor this default names an attribute, a partitionable pool reports no partitionSummary. Must include the domain qualifier.',
    )
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
