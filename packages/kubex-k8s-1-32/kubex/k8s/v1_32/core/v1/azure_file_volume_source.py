from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class AzureFileVolumeSource(BaseK8sModel):
    """AzureFile represents an Azure File Service mount on the host and bind mount to the pod."""

    read_only: bool | None = Field(
        default=None,
        alias="readOnly",
        description="readOnly defaults to false (read/write). ReadOnly here will force the ReadOnly setting in VolumeMounts.",
    )
    secret_name: str = Field(
        ...,
        alias="secretName",
        description="secretName is the name of secret that contains Azure Storage Account Name and Key",
    )
    share_name: str = Field(
        ..., alias="shareName", description="shareName is the azure share Name"
    )
