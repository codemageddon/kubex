from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class HostPathVolumeSource(BaseK8sModel):
    """Represents a host path mapped into a pod. Host path volumes do not support ownership management or SELinux relabeling."""

    path: str = Field(
        ...,
        alias="path",
        description="path of the directory on the host. If the path is a symlink, it will follow the link to the real path. More info: https://kubernetes.io/docs/concepts/storage/volumes#hostpath",
    )
    type_: str | None = Field(
        default=None,
        alias="type",
        description='type for HostPath Volume Defaults to "" More info: https://kubernetes.io/docs/concepts/storage/volumes#hostpath',
    )
