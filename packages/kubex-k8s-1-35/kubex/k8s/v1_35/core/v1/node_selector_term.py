from pydantic import Field

from kubex.k8s.v1_35.core.v1.node_selector_requirement import NodeSelectorRequirement
from kubex_core.models.base import BaseK8sModel


class NodeSelectorTerm(BaseK8sModel):
    """A null or empty node selector term matches no objects. The requirements of them are ANDed. The TopologySelectorTerm type implements a subset of the NodeSelectorTerm."""

    match_expressions: list[NodeSelectorRequirement] | None = Field(
        default=None,
        alias="matchExpressions",
        description="A list of node selector requirements by node's labels.",
    )
    match_fields: list[NodeSelectorRequirement] | None = Field(
        default=None,
        alias="matchFields",
        description="A list of node selector requirements by node's fields.",
    )
