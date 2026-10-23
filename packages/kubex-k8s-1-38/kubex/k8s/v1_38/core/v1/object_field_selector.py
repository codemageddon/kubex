from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class ObjectFieldSelector(BaseK8sModel):
    """ObjectFieldSelector selects an APIVersioned field of an object."""

    api_version: str | None = Field(
        default=None,
        alias="apiVersion",
        description='apiVersion is the version of the schema the FieldPath is written in terms of, defaults to "v1".',
    )
    field_path: str = Field(
        ...,
        alias="fieldPath",
        description="fieldPath is the path of the field to select in the specified API version.",
    )
