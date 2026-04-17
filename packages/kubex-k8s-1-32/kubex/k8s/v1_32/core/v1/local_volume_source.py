from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class LocalVolumeSource(BaseK8sModel):
    """Local represents directly-attached storage with node affinity"""

    fs_type: str | None = Field(
        default=None,
        alias="fsType",
        description='fsType is the filesystem type to mount. It applies only when the Path is a block device. Must be a filesystem type supported by the host operating system. Ex. "ext4", "xfs", "ntfs". The default value is to auto-select a filesystem if unspecified.',
    )
    path: str = Field(
        ...,
        alias="path",
        description="path of the full path to the volume on the node. It can be either a directory or block device (disk, partition, ...).",
    )
