from pydantic import Field

from kubex.k8s.v1_33.core.v1.node_selector import NodeSelector
from kubex_core.models.base import BaseK8sModel


class VolumeNodeAffinity(BaseK8sModel):
    """VolumeNodeAffinity defines constraints that limit what nodes this volume can be accessed from."""

    required: NodeSelector | None = Field(
        default=None,
        alias="required",
        description="required specifies hard node constraints that must be met.",
    )
