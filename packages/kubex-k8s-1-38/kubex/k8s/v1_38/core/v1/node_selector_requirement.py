from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class NodeSelectorRequirement(BaseK8sModel):
    """A node selector requirement is a selector that contains values, a key, and an operator that relates the key and values."""

    key: str = Field(
        ..., alias="key", description="The label key that the selector applies to."
    )
    operator: str = Field(
        ...,
        alias="operator",
        description="Represents a key's relationship to a set of values. Valid operators are In, NotIn, Exists, DoesNotExist. Gt, and Lt.",
    )
    values: list[str] | None = Field(
        default=None,
        alias="values",
        description="An array of string values. If the operator is In or NotIn, the values array must be non-empty. If the operator is Exists or DoesNotExist, the values array must be empty. If the operator is Gt or Lt, the values array must have a single element, which will be interpreted as an integer. This array is replaced during a strategic merge patch.",
    )
