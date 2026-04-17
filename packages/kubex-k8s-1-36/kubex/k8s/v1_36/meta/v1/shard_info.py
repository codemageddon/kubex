from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class ShardInfo(BaseK8sModel):
    """ShardInfo describes the shard selector that was applied to produce a list response. Its presence on a list response indicates the list is a filtered subset."""

    selector: str = Field(
        ...,
        alias="selector",
        description="selector is the shard selector string from the request, echoed back so clients can verify which shard they received and merge responses from multiple shards.",
    )
