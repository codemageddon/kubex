from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class CustomResourceColumnDefinition(BaseK8sModel):
    """CustomResourceColumnDefinition specifies a column for server side printing."""

    description: str | None = Field(
        default=None,
        alias="description",
        description="description is a human readable description of this column.",
    )
    format: str | None = Field(
        default=None,
        alias="format",
        description="format is an optional OpenAPI type definition for this column. The 'name' format is applied to the primary identifier column to assist in clients identifying column is the resource name. See https://github.com/OAI/OpenAPI-Specification/blob/master/versions/2.0.md#data-types for details.",
    )
    json_path: str = Field(
        ...,
        alias="jsonPath",
        description="jsonPath is a simple JSON path (i.e. with array notation) which is evaluated against each custom resource to produce the value for this column.",
    )
    name: str = Field(
        ..., alias="name", description="name is a human readable name for the column."
    )
    priority: int | None = Field(
        default=None,
        alias="priority",
        description="priority is an integer defining the relative importance of this column compared to others. Lower numbers are considered higher priority. Columns that may be omitted in limited space scenarios should be given a priority greater than 0.",
    )
    type_: str = Field(
        ...,
        alias="type",
        description="type is an OpenAPI type definition for this column. See https://github.com/OAI/OpenAPI-Specification/blob/master/versions/2.0.md#data-types for details.",
    )
