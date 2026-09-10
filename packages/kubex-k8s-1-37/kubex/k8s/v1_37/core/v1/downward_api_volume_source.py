from pydantic import Field

from kubex.k8s.v1_37.core.v1.downward_api_volume_file import DownwardAPIVolumeFile
from kubex_core.models.base import BaseK8sModel


class DownwardAPIVolumeSource(BaseK8sModel):
    """DownwardAPIVolumeSource represents a volume containing downward API info. Downward API volumes support ownership management and SELinux relabeling."""

    default_mode: int | None = Field(
        default=None,
        alias="defaultMode",
        description="Optional: mode bits to use on created files by default. Must be a Optional: mode bits used to set permissions on created files by default. Must be an octal value between 0000 and 0777 or a decimal value between 0 and 511. YAML accepts both octal and decimal values, JSON requires decimal values for mode bits. Defaults to 0644. Directories within the path are not affected by this setting. This might be in conflict with other options that affect the file mode, like fsGroup, and the result can be other mode bits set.",
    )
    default_user: int | None = Field(
        default=None,
        alias="defaultUser",
        description="defaultUser is Optional: The owner UID of the created files by default. The defaultUser field is only used as a fallback when the item-level user field is unset. (Alpha) This field requires the AtomicWriteVolumeUserFields feature gate to be enabled.",
    )
    items: list[DownwardAPIVolumeFile] | None = Field(
        default=None,
        alias="items",
        description="Items is a list of downward API volume file",
    )
