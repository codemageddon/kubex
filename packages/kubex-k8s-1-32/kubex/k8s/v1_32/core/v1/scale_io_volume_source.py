from pydantic import Field

from kubex.k8s.v1_32.core.v1.local_object_reference import LocalObjectReference
from kubex_core.models.base import BaseK8sModel


class ScaleIOVolumeSource(BaseK8sModel):
    """ScaleIOVolumeSource represents a persistent ScaleIO volume"""

    fs_type: str | None = Field(
        default=None,
        alias="fsType",
        description='fsType is the filesystem type to mount. Must be a filesystem type supported by the host operating system. Ex. "ext4", "xfs", "ntfs". Default is "xfs".',
    )
    gateway: str = Field(
        ...,
        alias="gateway",
        description="gateway is the host address of the ScaleIO API Gateway.",
    )
    protection_domain: str | None = Field(
        default=None,
        alias="protectionDomain",
        description="protectionDomain is the name of the ScaleIO Protection Domain for the configured storage.",
    )
    read_only: bool | None = Field(
        default=None,
        alias="readOnly",
        description="readOnly Defaults to false (read/write). ReadOnly here will force the ReadOnly setting in VolumeMounts.",
    )
    secret_ref: LocalObjectReference = Field(
        ...,
        alias="secretRef",
        description="secretRef references to the secret for ScaleIO user and other sensitive information. If this is not provided, Login operation will fail.",
    )
    ssl_enabled: bool | None = Field(
        default=None,
        alias="sslEnabled",
        description="sslEnabled Flag enable/disable SSL communication with Gateway, default false",
    )
    storage_mode: str | None = Field(
        default=None,
        alias="storageMode",
        description="storageMode indicates whether the storage for a volume should be ThickProvisioned or ThinProvisioned. Default is ThinProvisioned.",
    )
    storage_pool: str | None = Field(
        default=None,
        alias="storagePool",
        description="storagePool is the ScaleIO Storage Pool associated with the protection domain.",
    )
    system: str = Field(
        ...,
        alias="system",
        description="system is the name of the storage system as configured in ScaleIO.",
    )
    volume_name: str | None = Field(
        default=None,
        alias="volumeName",
        description="volumeName is the name of a volume already created in the ScaleIO system that is associated with this volume source.",
    )
