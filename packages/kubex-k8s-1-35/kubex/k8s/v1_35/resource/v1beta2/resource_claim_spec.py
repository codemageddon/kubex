from kubex.k8s.v1_35.resource.v1beta2.device_claim import DeviceClaim
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class ResourceClaimSpec(BaseK8sModel):
    """ResourceClaimSpec defines what is being requested in a ResourceClaim and how to configure it."""

    devices: DeviceClaim | None = Field(
        default=None,
        alias="devices",
        description="Devices defines how to request devices.",
    )
