from kubex.k8s.v1_32.resource.v1beta1.device_attribute import DeviceAttribute
from kubex.k8s.v1_32.resource.v1beta1.device_capacity import DeviceCapacity
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class BasicDevice(BaseK8sModel):
    """BasicDevice defines one device instance."""

    attributes: dict[str, DeviceAttribute] | None = Field(
        default=None,
        alias="attributes",
        description="Attributes defines the set of attributes for this device. The name of each attribute must be unique in that set. The maximum number of attributes and capacities combined is 32.",
    )
    capacity: dict[str, DeviceCapacity] | None = Field(
        default=None,
        alias="capacity",
        description="Capacity defines the set of capacities for this device. The name of each capacity must be unique in that set. The maximum number of attributes and capacities combined is 32.",
    )
