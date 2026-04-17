from kubex.k8s.v1_36.resource.v1beta1.opaque_device_configuration import (
    OpaqueDeviceConfiguration,
)
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class DeviceClaimConfiguration(BaseK8sModel):
    """DeviceClaimConfiguration is used for configuration parameters in DeviceClaim."""

    opaque: OpaqueDeviceConfiguration | None = Field(
        default=None,
        alias="opaque",
        description="Opaque provides driver-specific configuration parameters.",
    )
    requests: list[str] | None = Field(
        default=None,
        alias="requests",
        description="Requests lists the names of requests where the configuration applies. If empty, it applies to all requests. References to subrequests must include the name of the main request and may include the subrequest using the format <main request>[/<subrequest>]. If just the main request is given, the configuration applies to all subrequests.",
    )
