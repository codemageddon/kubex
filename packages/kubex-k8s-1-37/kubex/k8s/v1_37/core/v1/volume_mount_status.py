from kubex.k8s.v1_37.core.v1.volume_status import VolumeStatus
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class VolumeMountStatus(BaseK8sModel):
    """VolumeMountStatus shows status of volume mounts."""

    mount_path: str = Field(
        ...,
        alias="mountPath",
        description="MountPath corresponds to the original VolumeMount.",
    )
    name: str = Field(
        ...,
        alias="name",
        description="Name corresponds to the name of the original VolumeMount.",
    )
    read_only: bool | None = Field(
        default=None,
        alias="readOnly",
        description="ReadOnly corresponds to the original VolumeMount.",
    )
    recursive_read_only: str | None = Field(
        default=None,
        alias="recursiveReadOnly",
        description="RecursiveReadOnly must be set to Disabled, Enabled, or unspecified (for non-readonly mounts). An IfPossible value in the original VolumeMount must be translated to Disabled or Enabled, depending on the mount result.",
    )
    volume_status: VolumeStatus | None = Field(
        default=None,
        alias="volumeStatus",
        description="volumeStatus represents volume-type-specific status about the mounted volume.",
    )
