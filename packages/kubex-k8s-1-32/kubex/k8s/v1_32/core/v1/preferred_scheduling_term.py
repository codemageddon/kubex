from kubex.k8s.v1_32.core.v1.node_selector_term import NodeSelectorTerm
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class PreferredSchedulingTerm(BaseK8sModel):
    """An empty preferred scheduling term matches all objects with implicit weight 0 (i.e. it's a no-op). A null preferred scheduling term matches no objects (i.e. is also a no-op)."""

    preference: NodeSelectorTerm = Field(
        ...,
        alias="preference",
        description="A node selector term, associated with the corresponding weight.",
    )
    weight: int = Field(
        ...,
        alias="weight",
        description="Weight associated with matching the corresponding nodeSelectorTerm, in the range 1-100.",
    )
