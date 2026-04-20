from pydantic import Field

from kubex.k8s.v1_37.core.v1.local_object_reference import LocalObjectReference
from kubex_core.models.base import BaseK8sModel


class CephFSVolumeSource(BaseK8sModel):
    """Represents a Ceph Filesystem mount that lasts the lifetime of a pod Cephfs volumes do not support ownership management or SELinux relabeling."""

    monitors: list[str] = Field(
        ...,
        alias="monitors",
        description="monitors is Required: Monitors is a collection of Ceph monitors More info: https://examples.k8s.io/volumes/cephfs/README.md#how-to-use-it",
    )
    path: str | None = Field(
        default=None,
        alias="path",
        description="path is Optional: Used as the mounted root, rather than the full Ceph tree, default is /",
    )
    read_only: bool | None = Field(
        default=None,
        alias="readOnly",
        description="readOnly is Optional: Defaults to false (read/write). ReadOnly here will force the ReadOnly setting in VolumeMounts. More info: https://examples.k8s.io/volumes/cephfs/README.md#how-to-use-it",
    )
    secret_file: str | None = Field(
        default=None,
        alias="secretFile",
        description="secretFile is Optional: SecretFile is the path to key ring for User, default is /etc/ceph/user.secret More info: https://examples.k8s.io/volumes/cephfs/README.md#how-to-use-it",
    )
    secret_ref: LocalObjectReference | None = Field(
        default=None,
        alias="secretRef",
        description="secretRef is Optional: SecretRef is reference to the authentication secret for User, default is empty. More info: https://examples.k8s.io/volumes/cephfs/README.md#how-to-use-it",
    )
    user: str | None = Field(
        default=None,
        alias="user",
        description="user is optional: User is the rados user name, default is admin More info: https://examples.k8s.io/volumes/cephfs/README.md#how-to-use-it",
    )
