from pydantic import Field

from kubex.k8s.v1_34.core.v1.node_selector_term import NodeSelectorTerm
from kubex_core.models.base import BaseK8sModel


class NodeSelector(BaseK8sModel):
    """A node selector represents the union of the results of one or more label queries over a set of nodes; that is, it represents the OR of the selectors represented by the node selector terms."""

    node_selector_terms: list[NodeSelectorTerm] = Field(
        ...,
        alias="nodeSelectorTerms",
        description="Required. A list of node selector terms. The terms are ORed.",
    )
