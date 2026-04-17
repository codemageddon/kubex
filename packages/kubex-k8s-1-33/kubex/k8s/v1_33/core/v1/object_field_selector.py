from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class ObjectFieldSelector(BaseK8sModel):
    """ObjectFieldSelector selects an APIVersioned field of an object."""

    api_version: str | None = Field(
        default=None,
        alias="apiVersion",
        description='Version of the schema the FieldPath is written in terms of, defaults to "v1".',
    )
    field_path: str = Field(
        ...,
        alias="fieldPath",
        description="Path of the field to select in the specified API version.",
    )
