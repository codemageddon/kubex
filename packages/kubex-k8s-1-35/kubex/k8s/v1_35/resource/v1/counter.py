from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class Counter(BaseK8sModel):
    """Counter describes a quantity associated with a device."""

    value: str = Field(
        ...,
        alias="value",
        description="Value defines how much of a certain device counter is available.",
    )
