from pydantic import Field

from kubex.k8s.v1_37.storage.v1.storage_health import StorageHealth
from kubex_core.models.base import BaseK8sModel


class CSINodeStatus(BaseK8sModel):
    """CSINodeStatus contains health and status information for storage on a node."""

    storage_health: list[StorageHealth] | None = Field(
        default=None,
        alias="storageHealth",
        description="storageHealth contains backend health reports for CSI drivers registered on the node.",
    )
