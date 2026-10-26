from pydantic import Field

from kubex_core.models.base import BaseK8sModel
from kubex_core.models.types import Quantity


class Counter(BaseK8sModel):
    """Counter describes a quantity associated with a device."""

    value: Quantity = Field(
        ...,
        alias="value",
        description="value defines how much of a certain device counter is available.",
    )
