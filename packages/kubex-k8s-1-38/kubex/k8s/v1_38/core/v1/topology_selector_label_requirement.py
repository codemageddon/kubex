from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class TopologySelectorLabelRequirement(BaseK8sModel):
    """A topology selector requirement is a selector that matches given label. This is an alpha feature and may change in the future."""

    key: str = Field(
        ..., alias="key", description="The label key that the selector applies to."
    )
    values: list[str] = Field(
        ...,
        alias="values",
        description="An array of string values. One value must match the label to be selected. Each entry in Values is ORed.",
    )
