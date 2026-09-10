from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class AzureDiskVolumeSource(BaseK8sModel):
    """AzureDisk represents an Azure Data Disk mount on the host and bind mount to the pod."""

    caching_mode: str | None = Field(
        default=None,
        alias="cachingMode",
        description="cachingMode is the Host Caching mode: None, Read Only, Read Write.",
    )
    disk_name: str = Field(
        ...,
        alias="diskName",
        description="diskName is the Name of the data disk in the blob storage",
    )
    disk_uri: str = Field(
        ...,
        alias="diskURI",
        description="diskURI is the URI of data disk in the blob storage",
    )
    fs_type: str | None = Field(
        default=None,
        alias="fsType",
        description='fsType is Filesystem type to mount. Must be a filesystem type supported by the host operating system. Ex. "ext4", "xfs", "ntfs". Implicitly inferred to be "ext4" if unspecified.',
    )
    kind: str | None = Field(
        default=None,
        alias="kind",
        description="kind expected values are Shared: multiple blob disks per storage account Dedicated: single blob disk per storage account Managed: azure managed data disk (only in managed availability set). defaults to shared",
    )
    read_only: bool | None = Field(
        default=None,
        alias="readOnly",
        description="readOnly Defaults to false (read/write). ReadOnly here will force the ReadOnly setting in VolumeMounts.",
    )
