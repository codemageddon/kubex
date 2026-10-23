from pydantic import Field

from kubex.k8s.v1_38.core.v1.volume_status import VolumeStatus
from kubex_core.models.base import BaseK8sModel


class VolumeMountStatus(BaseK8sModel):
    """VolumeMountStatus shows status of volume mounts."""

    mount_path: str = Field(
        ...,
        alias="mountPath",
        description="mountPath corresponds to the original VolumeMount.",
    )
    name: str = Field(
        ...,
        alias="name",
        description="name corresponds to the name of the original VolumeMount.",
    )
    read_only: bool | None = Field(
        default=None,
        alias="readOnly",
        description="readOnly corresponds to the original VolumeMount.",
    )
    recursive_read_only: str | None = Field(
        default=None,
        alias="recursiveReadOnly",
        description="recursiveReadOnly must be set to Disabled, Enabled, or unspecified (for non-readonly mounts). An IfPossible value in the original VolumeMount must be translated to Disabled or Enabled, depending on the mount result.",
    )
    volume_status: VolumeStatus | None = Field(
        default=None,
        alias="volumeStatus",
        description="volumeStatus represents volume-type-specific status about the mounted volume.",
    )
