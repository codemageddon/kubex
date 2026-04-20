from pydantic import Field

from kubex.k8s.v1_36.resource.v1beta2.opaque_device_configuration import (
    OpaqueDeviceConfiguration,
)
from kubex_core.models.base import BaseK8sModel


class DeviceClassConfiguration(BaseK8sModel):
    """DeviceClassConfiguration is used in DeviceClass."""

    opaque: OpaqueDeviceConfiguration | None = Field(
        default=None,
        alias="opaque",
        description="Opaque provides driver-specific configuration parameters.",
    )
