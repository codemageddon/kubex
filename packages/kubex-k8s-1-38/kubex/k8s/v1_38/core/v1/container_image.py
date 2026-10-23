from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class ContainerImage(BaseK8sModel):
    """Describe a container image"""

    names: list[str] | None = Field(
        default=None,
        alias="names",
        description='names by which this image is known. e.g. ["kubernetes.example/hyperkube:v1.0.7", "cloud-vendor.registry.example/cloud-vendor/hyperkube:v1.0.7"]',
    )
    size_bytes: int | None = Field(
        default=None,
        alias="sizeBytes",
        description="sizeBytes is the size of the image in bytes.",
    )
