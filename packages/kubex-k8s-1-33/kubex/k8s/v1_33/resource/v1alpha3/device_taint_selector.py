from kubex.k8s.v1_33.resource.v1alpha3.device_selector import DeviceSelector
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class DeviceTaintSelector(BaseK8sModel):
    """DeviceTaintSelector defines which device(s) a DeviceTaintRule applies to. The empty selector matches all devices. Without a selector, no devices are matched."""

    device: str | None = Field(
        default=None,
        alias="device",
        description="If device is set, only devices with that name are selected. This field corresponds to slice.spec.devices[].name. Setting also driver and pool may be required to avoid ambiguity, but is not required.",
    )
    device_class_name: str | None = Field(
        default=None,
        alias="deviceClassName",
        description="If DeviceClassName is set, the selectors defined there must be satisfied by a device to be selected. This field corresponds to class.metadata.name.",
    )
    driver: str | None = Field(
        default=None,
        alias="driver",
        description="If driver is set, only devices from that driver are selected. This fields corresponds to slice.spec.driver.",
    )
    pool: str | None = Field(
        default=None,
        alias="pool",
        description="If pool is set, only devices in that pool are selected. Also setting the driver name may be useful to avoid ambiguity when different drivers use the same pool name, but this is not required because selecting pools from different drivers may also be useful, for example when drivers with node-local devices use the node name as their pool name.",
    )
    selectors: list[DeviceSelector] | None = Field(
        default=None,
        alias="selectors",
        description="Selectors contains the same selection criteria as a ResourceClaim. Currently, CEL expressions are supported. All of these selectors must be satisfied.",
    )
