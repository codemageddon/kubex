from pydantic import Field

from kubex.k8s.v1_36.meta.v1.condition import Condition
from kubex.k8s.v1_36.resource.v1alpha3.pool_status import PoolStatus
from kubex_core.models.base import BaseK8sModel


class ResourcePoolStatusRequestStatus(BaseK8sModel):
    """ResourcePoolStatusRequestStatus contains the calculated pool status information."""

    conditions: list[Condition] | None = Field(
        default=None,
        alias="conditions",
        description='Conditions provide information about the state of the request. A condition with type=Complete or type=Failed will always be set when the status is populated. Known condition types: - "Complete": True when the request has been processed successfully - "Failed": True when the request could not be processed',
    )
    pool_count: int = Field(
        ...,
        alias="poolCount",
        description="PoolCount is the total number of pools that matched the filter criteria, regardless of truncation. This helps users understand how many pools exist even when the response is truncated. A value of 0 means no pools matched the filter criteria.",
    )
    pools: list[PoolStatus] | None = Field(
        default=None,
        alias="pools",
        description="Pools contains the first `spec.limit` matching pools, sorted by driver then pool name. If `len(pools) < poolCount`, the list was truncated. When omitted, no pools matched the request filters.",
    )
