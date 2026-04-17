from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class FCVolumeSource(BaseK8sModel):
    """Represents a Fibre Channel volume. Fibre Channel volumes can only be mounted as read/write once. Fibre Channel volumes support ownership management and SELinux relabeling."""

    fs_type: str | None = Field(
        default=None,
        alias="fsType",
        description='fsType is the filesystem type to mount. Must be a filesystem type supported by the host operating system. Ex. "ext4", "xfs", "ntfs". Implicitly inferred to be "ext4" if unspecified.',
    )
    lun: int | None = Field(
        default=None, alias="lun", description="lun is Optional: FC target lun number"
    )
    read_only: bool | None = Field(
        default=None,
        alias="readOnly",
        description="readOnly is Optional: Defaults to false (read/write). ReadOnly here will force the ReadOnly setting in VolumeMounts.",
    )
    target_wwns: list[str] | None = Field(
        default=None,
        alias="targetWWNs",
        description="targetWWNs is Optional: FC target worldwide names (WWNs)",
    )
    wwids: list[str] | None = Field(
        default=None,
        alias="wwids",
        description="wwids Optional: FC volume world wide identifiers (wwids) Either wwids or combination of targetWWNs and lun must be set, but not both simultaneously.",
    )
