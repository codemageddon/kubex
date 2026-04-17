from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class GlusterfsVolumeSource(BaseK8sModel):
    """Represents a Glusterfs mount that lasts the lifetime of a pod. Glusterfs volumes do not support ownership management or SELinux relabeling."""

    endpoints: str = Field(
        ...,
        alias="endpoints",
        description="endpoints is the endpoint name that details Glusterfs topology. More info: https://examples.k8s.io/volumes/glusterfs/README.md#create-a-pod",
    )
    path: str = Field(
        ...,
        alias="path",
        description="path is the Glusterfs volume path. More info: https://examples.k8s.io/volumes/glusterfs/README.md#create-a-pod",
    )
    read_only: bool | None = Field(
        default=None,
        alias="readOnly",
        description="readOnly here will force the Glusterfs volume to be mounted with read-only permissions. Defaults to false. More info: https://examples.k8s.io/volumes/glusterfs/README.md#create-a-pod",
    )
