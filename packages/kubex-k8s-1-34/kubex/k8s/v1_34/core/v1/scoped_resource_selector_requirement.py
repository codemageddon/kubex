from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class ScopedResourceSelectorRequirement(BaseK8sModel):
    """A scoped-resource selector requirement is a selector that contains values, a scope name, and an operator that relates the scope name and values."""

    operator: str = Field(
        ...,
        alias="operator",
        description="Represents a scope's relationship to a set of values. Valid operators are In, NotIn, Exists, DoesNotExist.",
    )
    scope_name: str = Field(
        ...,
        alias="scopeName",
        description="The name of the scope that the selector applies to.",
    )
    values: list[str] | None = Field(
        default=None,
        alias="values",
        description="An array of string values. If the operator is In or NotIn, the values array must be non-empty. If the operator is Exists or DoesNotExist, the values array must be empty. This array is replaced during a strategic merge patch.",
    )
