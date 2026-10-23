from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class AttachedVolume(BaseK8sModel):
    """AttachedVolume describes a volume attached to a node"""

    device_path: str = Field(
        ...,
        alias="devicePath",
        description="devicePath represents the path where the attached volume is available on the node. On Linux nodes, this is the host block-device node (e.g. /dev/xvdX) that the kubelet uses to mount and format the volume. On Windows nodes there is no /dev device tree, so this carries the CSI VolumeID (the attach identity reported by the CSI driver) instead of a device path.",
    )
    name: str = Field(..., alias="name", description="name of the attached volume")
