from pydantic import Field

from kubex.k8s.v1_36.resource.v1beta1.device_claim_configuration import (
    DeviceClaimConfiguration,
)
from kubex.k8s.v1_36.resource.v1beta1.device_constraint import DeviceConstraint
from kubex.k8s.v1_36.resource.v1beta1.device_request import DeviceRequest
from kubex_core.models.base import BaseK8sModel


class DeviceClaim(BaseK8sModel):
    """DeviceClaim defines how to request devices with a ResourceClaim."""

    config: list[DeviceClaimConfiguration] | None = Field(
        default=None,
        alias="config",
        description="This field holds configuration for multiple potential drivers which could satisfy requests in this claim. It is ignored while allocating the claim.",
    )
    constraints: list[DeviceConstraint] | None = Field(
        default=None,
        alias="constraints",
        description="These constraints must be satisfied by the set of devices that get allocated for the claim.",
    )
    requests: list[DeviceRequest] | None = Field(
        default=None,
        alias="requests",
        description="Requests represent individual requests for distinct devices which must all be satisfied. If empty, nothing needs to be allocated.",
    )
