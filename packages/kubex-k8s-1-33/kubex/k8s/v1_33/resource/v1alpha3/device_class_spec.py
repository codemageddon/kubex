from kubex.k8s.v1_33.resource.v1alpha3.device_class_configuration import (
    DeviceClassConfiguration,
)
from kubex.k8s.v1_33.resource.v1alpha3.device_selector import DeviceSelector
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class DeviceClassSpec(BaseK8sModel):
    """DeviceClassSpec is used in a [DeviceClass] to define what can be allocated and how to configure it."""

    config: list[DeviceClassConfiguration] | None = Field(
        default=None,
        alias="config",
        description="Config defines configuration parameters that apply to each device that is claimed via this class. Some classses may potentially be satisfied by multiple drivers, so each instance of a vendor configuration applies to exactly one driver. They are passed to the driver, but are not considered while allocating the claim.",
    )
    selectors: list[DeviceSelector] | None = Field(
        default=None,
        alias="selectors",
        description="Each selector must be satisfied by a device which is claimed via this class.",
    )
