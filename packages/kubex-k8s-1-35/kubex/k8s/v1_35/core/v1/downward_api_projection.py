from pydantic import Field

from kubex.k8s.v1_35.core.v1.downward_api_volume_file import DownwardAPIVolumeFile
from kubex_core.models.base import BaseK8sModel


class DownwardAPIProjection(BaseK8sModel):
    """Represents downward API info for projecting into a projected volume. Note that this is identical to a downwardAPI volume source without the default mode."""

    items: list[DownwardAPIVolumeFile] | None = Field(
        default=None,
        alias="items",
        description="Items is a list of DownwardAPIVolume file",
    )
