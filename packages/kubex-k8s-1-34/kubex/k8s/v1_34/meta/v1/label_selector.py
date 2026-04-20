from pydantic import Field

from kubex.k8s.v1_34.meta.v1.label_selector_requirement import LabelSelectorRequirement
from kubex_core.models.base import BaseK8sModel


class LabelSelector(BaseK8sModel):
    """A label selector is a label query over a set of resources. The result of matchLabels and matchExpressions are ANDed. An empty label selector matches all objects. A null label selector matches no objects."""

    match_expressions: list[LabelSelectorRequirement] | None = Field(
        default=None,
        alias="matchExpressions",
        description="matchExpressions is a list of label selector requirements. The requirements are ANDed.",
    )
    match_labels: dict[str, str] | None = Field(
        default=None,
        alias="matchLabels",
        description='matchLabels is a map of {key,value} pairs. A single {key,value} in the matchLabels map is equivalent to an element of matchExpressions, whose key field is "key", the operator is "In", and the values array contains only "value". The requirements are ANDed.',
    )
