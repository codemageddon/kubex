from pydantic import Field

from kubex.k8s.v1_37.core.v1.secret_reference import SecretReference
from kubex_core.models.base import BaseK8sModel


class CSIPersistentVolumeSource(BaseK8sModel):
    """Represents storage that is managed by an external CSI volume driver"""

    controller_expand_secret_ref: SecretReference | None = Field(
        default=None,
        alias="controllerExpandSecretRef",
        description="controllerExpandSecretRef is a reference to the secret object containing sensitive information to pass to the CSI driver to complete the CSI ControllerExpandVolume call. This field is optional, and may be empty if no secret is required. If the secret object contains more than one secret, all secrets are passed.",
    )
    controller_publish_secret_ref: SecretReference | None = Field(
        default=None,
        alias="controllerPublishSecretRef",
        description="controllerPublishSecretRef is a reference to the secret object containing sensitive information to pass to the CSI driver to complete the CSI ControllerPublishVolume and ControllerUnpublishVolume calls. This field is optional, and may be empty if no secret is required. If the secret object contains more than one secret, all secrets are passed.",
    )
    driver: str = Field(
        ...,
        alias="driver",
        description="driver is the name of the driver to use for this volume. Required.",
    )
    fs_type: str | None = Field(
        default=None,
        alias="fsType",
        description='fsType to mount. Must be a filesystem type supported by the host operating system. Ex. "ext4", "xfs", "ntfs".',
    )
    node_expand_secret_ref: SecretReference | None = Field(
        default=None,
        alias="nodeExpandSecretRef",
        description="nodeExpandSecretRef is a reference to the secret object containing sensitive information to pass to the CSI driver to complete the CSI NodeExpandVolume call. This field is optional, may be omitted if no secret is required. If the secret object contains more than one secret, all secrets are passed.",
    )
    node_publish_secret_ref: SecretReference | None = Field(
        default=None,
        alias="nodePublishSecretRef",
        description="nodePublishSecretRef is a reference to the secret object containing sensitive information to pass to the CSI driver to complete the CSI NodePublishVolume and NodeUnpublishVolume calls. This field is optional, and may be empty if no secret is required. If the secret object contains more than one secret, all secrets are passed.",
    )
    node_stage_secret_ref: SecretReference | None = Field(
        default=None,
        alias="nodeStageSecretRef",
        description="nodeStageSecretRef is a reference to the secret object containing sensitive information to pass to the CSI driver to complete the CSI NodeStageVolume and NodeStageVolume and NodeUnstageVolume calls. This field is optional, and may be empty if no secret is required. If the secret object contains more than one secret, all secrets are passed.",
    )
    read_only: bool | None = Field(
        default=None,
        alias="readOnly",
        description="readOnly value to pass to ControllerPublishVolumeRequest. Defaults to false (read/write).",
    )
    volume_attributes: dict[str, str] | None = Field(
        default=None,
        alias="volumeAttributes",
        description="volumeAttributes of the volume to publish.",
    )
    volume_handle: str = Field(
        ...,
        alias="volumeHandle",
        description="volumeHandle is the unique volume name returned by the CSI volume plugin’s CreateVolume to refer to the volume on all subsequent calls. Required.",
    )
