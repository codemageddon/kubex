from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class ShareableCapacityStatus(BaseK8sModel):
    """ShareableCapacityStatus reports aggregate amounts for a single shareable capacity key."""

    available: str = Field(
        ...,
        alias="available",
        description="available is Total minus Consumed, never negative.",
    )
    consumed: str = Field(
        ...,
        alias="consumed",
        description="consumed is the amount drawn by current allocations.",
    )
    name: str = Field(..., alias="name", description="name is the capacity name.")
    total: str = Field(
        ...,
        alias="total",
        description="total is the sum of this capacity across shareable devices in the pool.",
    )
