from pydantic import Field

from kubex.k8s.v1_33.resource.v1alpha3.device_taint import DeviceTaint
from kubex.k8s.v1_33.resource.v1alpha3.device_taint_selector import DeviceTaintSelector
from kubex_core.models.base import BaseK8sModel


class DeviceTaintRuleSpec(BaseK8sModel):
    """DeviceTaintRuleSpec specifies the selector and one taint."""

    device_selector: DeviceTaintSelector | None = Field(
        default=None,
        alias="deviceSelector",
        description="DeviceSelector defines which device(s) the taint is applied to. All selector criteria must be satified for a device to match. The empty selector matches all devices. Without a selector, no devices are matches.",
    )
    taint: DeviceTaint = Field(
        ...,
        alias="taint",
        description="The taint that gets applied to matching devices.",
    )
