from pydantic import Field

from kubex.k8s.v1_37.storage.v1.storage_health_condition import StorageHealthCondition
from kubex_core.models.base import BaseK8sModel


class StorageHealth(BaseK8sModel):
    """StorageHealth contains storage backend health reported by a CSI driver on a node."""

    health_conditions: list[StorageHealthCondition] | None = Field(
        default=None,
        alias="healthConditions",
        description="healthConditions are the adverse storage backend conditions reported by the CSI driver. At most 16 conditions may be reported.",
    )
    name: str = Field(
        ...,
        alias="name",
        description="name is the CSI driver name, matching CSINodeDriver.name.",
    )
