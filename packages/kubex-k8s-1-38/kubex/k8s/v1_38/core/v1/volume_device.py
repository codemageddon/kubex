from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class VolumeDevice(BaseK8sModel):
    """volumeDevice describes a mapping of a raw block device within a container."""

    device_path: str = Field(
        ...,
        alias="devicePath",
        description="devicePath is the path inside of the container that the device will be mapped to.",
    )
    name: str = Field(
        ...,
        alias="name",
        description="name must match the name of a persistentVolumeClaim in the pod",
    )
