from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class VsphereVirtualDiskVolumeSource(BaseK8sModel):
    """Represents a vSphere volume resource."""

    fs_type: str | None = Field(
        default=None,
        alias="fsType",
        description='fsType is filesystem type to mount. Must be a filesystem type supported by the host operating system. Ex. "ext4", "xfs", "ntfs". Implicitly inferred to be "ext4" if unspecified.',
    )
    storage_policy_id: str | None = Field(
        default=None,
        alias="storagePolicyID",
        description="storagePolicyID is the storage Policy Based Management (SPBM) profile ID associated with the StoragePolicyName.",
    )
    storage_policy_name: str | None = Field(
        default=None,
        alias="storagePolicyName",
        description="storagePolicyName is the storage Policy Based Management (SPBM) profile name.",
    )
    volume_path: str = Field(
        ...,
        alias="volumePath",
        description="volumePath is the path that identifies vSphere volume vmdk",
    )
