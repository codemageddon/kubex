from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class NodeSwapStatus(BaseK8sModel):
    """NodeSwapStatus represents swap memory information."""

    capacity: int | None = Field(
        default=None,
        alias="capacity",
        description="Total amount of swap memory in bytes.",
    )
