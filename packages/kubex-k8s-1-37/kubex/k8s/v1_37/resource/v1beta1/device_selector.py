from kubex.k8s.v1_37.resource.v1beta1.cel_device_selector import CELDeviceSelector
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class DeviceSelector(BaseK8sModel):
    """DeviceSelector must have exactly one field set."""

    cel: CELDeviceSelector | None = Field(
        default=None,
        alias="cel",
        description="CEL contains a CEL expression for selecting a device.",
    )
