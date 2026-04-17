from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class ImageVolumeStatus(BaseK8sModel):
    """ImageVolumeStatus represents the image-based volume status."""

    image_ref: str = Field(
        ...,
        alias="imageRef",
        description="ImageRef is the digest of the image used for this volume. It should have a value that's similar to the pod's status.containerStatuses[i].imageID. The ImageRef length should not exceed 256 characters.",
    )
