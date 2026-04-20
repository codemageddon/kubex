from pydantic import Field

from kubex.k8s.v1_34.core.v1.scope_selector import ScopeSelector
from kubex_core.models.base import BaseK8sModel


class ResourceQuotaSpec(BaseK8sModel):
    """ResourceQuotaSpec defines the desired hard limits to enforce for Quota."""

    hard: dict[str, str] | None = Field(
        default=None,
        alias="hard",
        description="hard is the set of desired hard limits for each named resource. More info: https://kubernetes.io/docs/concepts/policy/resource-quotas/",
    )
    scope_selector: ScopeSelector | None = Field(
        default=None,
        alias="scopeSelector",
        description="scopeSelector is also a collection of filters like scopes that must match each object tracked by a quota but expressed using ScopeSelectorOperator in combination with possible values. For a resource to match, both scopes AND scopeSelector (if specified in spec), must be matched.",
    )
    scopes: list[str] | None = Field(
        default=None,
        alias="scopes",
        description="A collection of filters that must match each object tracked by a quota. If not specified, the quota matches all objects.",
    )
