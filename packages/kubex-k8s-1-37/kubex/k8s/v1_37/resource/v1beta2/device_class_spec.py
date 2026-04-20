from pydantic import Field

from kubex.k8s.v1_37.resource.v1beta2.device_class_configuration import (
    DeviceClassConfiguration,
)
from kubex.k8s.v1_37.resource.v1beta2.device_selector import DeviceSelector
from kubex_core.models.base import BaseK8sModel


class DeviceClassSpec(BaseK8sModel):
    """DeviceClassSpec is used in a [DeviceClass] to define what can be allocated and how to configure it."""

    config: list[DeviceClassConfiguration] | None = Field(
        default=None,
        alias="config",
        description="Config defines configuration parameters that apply to each device that is claimed via this class. Some classses may potentially be satisfied by multiple drivers, so each instance of a vendor configuration applies to exactly one driver. They are passed to the driver, but are not considered while allocating the claim.",
    )
    extended_resource_name: str | None = Field(
        default=None,
        alias="extendedResourceName",
        description="ExtendedResourceName is the extended resource name for the devices of this class. The devices of this class can be used to satisfy a pod's extended resource requests. It has the same format as the name of a pod's extended resource. It should be unique among all the device classes in a cluster. If two device classes have the same name, then the class created later is picked to satisfy a pod's extended resource requests. If two classes are created at the same time, then the name of the class lexicographically sorted first is picked. This is a beta field.",
    )
    selectors: list[DeviceSelector] | None = Field(
        default=None,
        alias="selectors",
        description="Each selector must be satisfied by a device which is claimed via this class.",
    )
