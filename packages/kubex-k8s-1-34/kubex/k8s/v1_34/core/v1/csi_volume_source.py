from kubex.k8s.v1_34.core.v1.local_object_reference import LocalObjectReference
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class CSIVolumeSource(BaseK8sModel):
    """Represents a source location of a volume to mount, managed by an external CSI driver"""

    driver: str = Field(
        ...,
        alias="driver",
        description="driver is the name of the CSI driver that handles this volume. Consult with your admin for the correct name as registered in the cluster.",
    )
    fs_type: str | None = Field(
        default=None,
        alias="fsType",
        description='fsType to mount. Ex. "ext4", "xfs", "ntfs". If not provided, the empty value is passed to the associated CSI driver which will determine the default filesystem to apply.',
    )
    node_publish_secret_ref: LocalObjectReference | None = Field(
        default=None,
        alias="nodePublishSecretRef",
        description="nodePublishSecretRef is a reference to the secret object containing sensitive information to pass to the CSI driver to complete the CSI NodePublishVolume and NodeUnpublishVolume calls. This field is optional, and may be empty if no secret is required. If the secret object contains more than one secret, all secret references are passed.",
    )
    read_only: bool | None = Field(
        default=None,
        alias="readOnly",
        description="readOnly specifies a read-only configuration for the volume. Defaults to false (read/write).",
    )
    volume_attributes: dict[str, str] | None = Field(
        default=None,
        alias="volumeAttributes",
        description="volumeAttributes stores driver-specific properties that are passed to the CSI driver. Consult your driver's documentation for supported values.",
    )
