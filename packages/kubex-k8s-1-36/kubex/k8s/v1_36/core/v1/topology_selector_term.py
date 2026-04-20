from pydantic import Field

from kubex.k8s.v1_36.core.v1.topology_selector_label_requirement import (
    TopologySelectorLabelRequirement,
)
from kubex_core.models.base import BaseK8sModel


class TopologySelectorTerm(BaseK8sModel):
    """A topology selector term represents the result of label queries. A null or empty topology selector term matches no objects. The requirements of them are ANDed. It provides a subset of functionality as NodeSelectorTerm. This is an alpha feature and may change in the future."""

    match_label_expressions: list[TopologySelectorLabelRequirement] | None = Field(
        default=None,
        alias="matchLabelExpressions",
        description="A list of topology selector requirements by labels.",
    )
