from kubex.k8s.v1_32.storage.v1.csi_node_driver import CSINodeDriver
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class CSINodeSpec(BaseK8sModel):
    """CSINodeSpec holds information about the specification of all CSI drivers installed on a node"""

    drivers: list[CSINodeDriver] = Field(
        ...,
        alias="drivers",
        description="drivers is a list of information of all CSI Drivers existing on a node. If all drivers in the list are uninstalled, this can become empty.",
    )
