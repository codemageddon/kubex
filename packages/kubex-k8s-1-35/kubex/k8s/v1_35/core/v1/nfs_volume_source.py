from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class NFSVolumeSource(BaseK8sModel):
    """Represents an NFS mount that lasts the lifetime of a pod. NFS volumes do not support ownership management or SELinux relabeling."""

    path: str = Field(
        ...,
        alias="path",
        description="path that is exported by the NFS server. More info: https://kubernetes.io/docs/concepts/storage/volumes#nfs",
    )
    read_only: bool | None = Field(
        default=None,
        alias="readOnly",
        description="readOnly here will force the NFS export to be mounted with read-only permissions. Defaults to false. More info: https://kubernetes.io/docs/concepts/storage/volumes#nfs",
    )
    server: str = Field(
        ...,
        alias="server",
        description="server is the hostname or IP address of the NFS server. More info: https://kubernetes.io/docs/concepts/storage/volumes#nfs",
    )
