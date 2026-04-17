from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class FlockerVolumeSource(BaseK8sModel):
    """Represents a Flocker volume mounted by the Flocker agent. One and only one of datasetName and datasetUUID should be set. Flocker volumes do not support ownership management or SELinux relabeling."""

    dataset_name: str | None = Field(
        default=None,
        alias="datasetName",
        description="datasetName is Name of the dataset stored as metadata -> name on the dataset for Flocker should be considered as deprecated",
    )
    dataset_uuid: str | None = Field(
        default=None,
        alias="datasetUUID",
        description="datasetUUID is the UUID of the dataset. This is unique identifier of a Flocker dataset",
    )
