from kubex.k8s.v1_35.core.v1.secret_reference import SecretReference
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class FlexPersistentVolumeSource(BaseK8sModel):
    """FlexPersistentVolumeSource represents a generic persistent volume resource that is provisioned/attached using an exec based plugin."""

    driver: str = Field(
        ...,
        alias="driver",
        description="driver is the name of the driver to use for this volume.",
    )
    fs_type: str | None = Field(
        default=None,
        alias="fsType",
        description='fsType is the Filesystem type to mount. Must be a filesystem type supported by the host operating system. Ex. "ext4", "xfs", "ntfs". The default filesystem depends on FlexVolume script.',
    )
    options: dict[str, str] | None = Field(
        default=None,
        alias="options",
        description="options is Optional: this field holds extra command options if any.",
    )
    read_only: bool | None = Field(
        default=None,
        alias="readOnly",
        description="readOnly is Optional: defaults to false (read/write). ReadOnly here will force the ReadOnly setting in VolumeMounts.",
    )
    secret_ref: SecretReference | None = Field(
        default=None,
        alias="secretRef",
        description="secretRef is Optional: SecretRef is reference to the secret object containing sensitive information to pass to the plugin scripts. This may be empty if no secret object is specified. If the secret object contains more than one secret, all secrets are passed to the plugin scripts.",
    )
