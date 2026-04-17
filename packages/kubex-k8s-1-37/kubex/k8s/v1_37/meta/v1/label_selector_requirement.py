from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class LabelSelectorRequirement(BaseK8sModel):
    """A label selector requirement is a selector that contains values, a key, and an operator that relates the key and values."""

    key: str = Field(
        ...,
        alias="key",
        description="key is the label key that the selector applies to.",
    )
    operator: str = Field(
        ...,
        alias="operator",
        description="operator represents a key's relationship to a set of values. Valid operators are In, NotIn, Exists and DoesNotExist.",
    )
    values: list[str] | None = Field(
        default=None,
        alias="values",
        description="values is an array of string values. If the operator is In or NotIn, the values array must be non-empty. If the operator is Exists or DoesNotExist, the values array must be empty. This array is replaced during a strategic merge patch.",
    )
