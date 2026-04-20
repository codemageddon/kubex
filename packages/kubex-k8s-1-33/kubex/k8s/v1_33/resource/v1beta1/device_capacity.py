from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class DeviceCapacity(BaseK8sModel):
    """DeviceCapacity describes a quantity associated with a device."""

    value: str = Field(
        ...,
        alias="value",
        description="Value defines how much of a certain device capacity is available.",
    )
