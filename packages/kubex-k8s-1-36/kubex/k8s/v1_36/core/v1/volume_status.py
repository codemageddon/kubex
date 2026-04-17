from kubex.k8s.v1_36.core.v1.image_volume_status import ImageVolumeStatus
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class VolumeStatus(BaseK8sModel):
    """VolumeStatus represents the status of a mounted volume. At most one of its members must be specified."""

    image: ImageVolumeStatus | None = Field(
        default=None,
        alias="image",
        description="image represents an OCI object (a container image or artifact) pulled and mounted on the kubelet's host machine.",
    )
