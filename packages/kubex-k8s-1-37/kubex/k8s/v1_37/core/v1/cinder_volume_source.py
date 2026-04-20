from pydantic import Field

from kubex.k8s.v1_37.core.v1.local_object_reference import LocalObjectReference
from kubex_core.models.base import BaseK8sModel


class CinderVolumeSource(BaseK8sModel):
    """Represents a cinder volume resource in Openstack. A Cinder volume must exist before mounting to a container. The volume must also be in the same region as the kubelet. Cinder volumes support ownership management and SELinux relabeling."""

    fs_type: str | None = Field(
        default=None,
        alias="fsType",
        description='fsType is the filesystem type to mount. Must be a filesystem type supported by the host operating system. Examples: "ext4", "xfs", "ntfs". Implicitly inferred to be "ext4" if unspecified. More info: https://examples.k8s.io/mysql-cinder-pd/README.md',
    )
    read_only: bool | None = Field(
        default=None,
        alias="readOnly",
        description="readOnly defaults to false (read/write). ReadOnly here will force the ReadOnly setting in VolumeMounts. More info: https://examples.k8s.io/mysql-cinder-pd/README.md",
    )
    secret_ref: LocalObjectReference | None = Field(
        default=None,
        alias="secretRef",
        description="secretRef is optional: points to a secret object containing parameters used to connect to OpenStack.",
    )
    volume_id: str = Field(
        ...,
        alias="volumeID",
        description="volumeID used to identify the volume in cinder. More info: https://examples.k8s.io/mysql-cinder-pd/README.md",
    )
