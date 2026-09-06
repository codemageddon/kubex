from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class AttachedVolume(BaseK8sModel):
    """AttachedVolume describes a volume attached to a node"""

    device_path: str = Field(
        ...,
        alias="devicePath",
        description="DevicePath represents the device path where the volume should be available",
    )
    name: str = Field(..., alias="name", description="Name of the attached volume")
