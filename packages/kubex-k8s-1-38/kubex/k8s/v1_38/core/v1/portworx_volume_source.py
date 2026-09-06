from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class PortworxVolumeSource(BaseK8sModel):
    """PortworxVolumeSource represents a Portworx volume resource."""

    fs_type: str | None = Field(
        default=None,
        alias="fsType",
        description='fSType represents the filesystem type to mount Must be a filesystem type supported by the host operating system. Ex. "ext4", "xfs". Implicitly inferred to be "ext4" if unspecified.',
    )
    read_only: bool | None = Field(
        default=None,
        alias="readOnly",
        description="readOnly defaults to false (read/write). ReadOnly here will force the ReadOnly setting in VolumeMounts.",
    )
    volume_id: str = Field(
        ...,
        alias="volumeID",
        description="volumeID uniquely identifies a Portworx volume",
    )
