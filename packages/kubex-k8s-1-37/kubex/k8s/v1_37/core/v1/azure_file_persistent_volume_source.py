from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class AzureFilePersistentVolumeSource(BaseK8sModel):
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
    secret_namespace: str | None = Field(
        default=None,
        alias="secretNamespace",
        description="secretNamespace is the namespace of the secret that contains Azure Storage Account Name and Key default is the same as the Pod",
    )
    share_name: str = Field(
        ..., alias="shareName", description="shareName is the azure Share Name"
    )
