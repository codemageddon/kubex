from kubex.k8s.v1_32.core.v1.local_object_reference import LocalObjectReference
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class RBDVolumeSource(BaseK8sModel):
    """Represents a Rados Block Device mount that lasts the lifetime of a pod. RBD volumes support ownership management and SELinux relabeling."""

    fs_type: str | None = Field(
        default=None,
        alias="fsType",
        description='fsType is the filesystem type of the volume that you want to mount. Tip: Ensure that the filesystem type is supported by the host operating system. Examples: "ext4", "xfs", "ntfs". Implicitly inferred to be "ext4" if unspecified. More info: https://kubernetes.io/docs/concepts/storage/volumes#rbd',
    )
    image: str = Field(
        ...,
        alias="image",
        description="image is the rados image name. More info: https://examples.k8s.io/volumes/rbd/README.md#how-to-use-it",
    )
    keyring: str | None = Field(
        default=None,
        alias="keyring",
        description="keyring is the path to key ring for RBDUser. Default is /etc/ceph/keyring. More info: https://examples.k8s.io/volumes/rbd/README.md#how-to-use-it",
    )
    monitors: list[str] = Field(
        ...,
        alias="monitors",
        description="monitors is a collection of Ceph monitors. More info: https://examples.k8s.io/volumes/rbd/README.md#how-to-use-it",
    )
    pool: str | None = Field(
        default=None,
        alias="pool",
        description="pool is the rados pool name. Default is rbd. More info: https://examples.k8s.io/volumes/rbd/README.md#how-to-use-it",
    )
    read_only: bool | None = Field(
        default=None,
        alias="readOnly",
        description="readOnly here will force the ReadOnly setting in VolumeMounts. Defaults to false. More info: https://examples.k8s.io/volumes/rbd/README.md#how-to-use-it",
    )
    secret_ref: LocalObjectReference | None = Field(
        default=None,
        alias="secretRef",
        description="secretRef is name of the authentication secret for RBDUser. If provided overrides keyring. Default is nil. More info: https://examples.k8s.io/volumes/rbd/README.md#how-to-use-it",
    )
    user: str | None = Field(
        default=None,
        alias="user",
        description="user is the rados user name. Default is admin. More info: https://examples.k8s.io/volumes/rbd/README.md#how-to-use-it",
    )
