from pydantic import Field

from kubex.k8s.v1_36.core.v1.object_reference import ObjectReference
from kubex_core.models.base import BaseK8sModel


class StorageOSPersistentVolumeSource(BaseK8sModel):
    """Represents a StorageOS persistent volume resource."""

    fs_type: str | None = Field(
        default=None,
        alias="fsType",
        description='fsType is the filesystem type to mount. Must be a filesystem type supported by the host operating system. Ex. "ext4", "xfs", "ntfs". Implicitly inferred to be "ext4" if unspecified.',
    )
    read_only: bool | None = Field(
        default=None,
        alias="readOnly",
        description="readOnly defaults to false (read/write). ReadOnly here will force the ReadOnly setting in VolumeMounts.",
    )
    secret_ref: ObjectReference | None = Field(
        default=None,
        alias="secretRef",
        description="secretRef specifies the secret to use for obtaining the StorageOS API credentials. If not specified, default values will be attempted.",
    )
    volume_name: str | None = Field(
        default=None,
        alias="volumeName",
        description="volumeName is the human-readable name of the StorageOS volume. Volume names are only unique within a namespace.",
    )
    volume_namespace: str | None = Field(
        default=None,
        alias="volumeNamespace",
        description='volumeNamespace specifies the scope of the volume within StorageOS. If no namespace is specified then the Pod\'s namespace will be used. This allows the Kubernetes name scoping to be mirrored within StorageOS for tighter integration. Set VolumeName to any name to override the default behaviour. Set to "default" if you are not using namespaces within StorageOS. Namespaces that do not pre-exist within StorageOS will be created.',
    )
