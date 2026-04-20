from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class PhotonPersistentDiskVolumeSource(BaseK8sModel):
    """Represents a Photon Controller persistent disk resource."""

    fs_type: str | None = Field(
        default=None,
        alias="fsType",
        description='fsType is the filesystem type to mount. Must be a filesystem type supported by the host operating system. Ex. "ext4", "xfs", "ntfs". Implicitly inferred to be "ext4" if unspecified.',
    )
    pd_id: str = Field(
        ...,
        alias="pdID",
        description="pdID is the ID that identifies Photon Controller persistent disk",
    )
