from pydantic import Field

from kubex.k8s.v1_37.core.v1.scoped_resource_selector_requirement import (
    ScopedResourceSelectorRequirement,
)
from kubex_core.models.base import BaseK8sModel


class ScopeSelector(BaseK8sModel):
    """A scope selector represents the AND of the selectors represented by the scoped-resource selector requirements."""

    match_expressions: list[ScopedResourceSelectorRequirement] | None = Field(
        default=None,
        alias="matchExpressions",
        description="A list of scope selector requirements by scope of the resources.",
    )
