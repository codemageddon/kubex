from pydantic import Field

from kubex.k8s.v1_32.apiextensions_k8s_io.v1.json_schema_props import JSONSchemaProps
from kubex_core.models.base import BaseK8sModel


class CustomResourceValidation(BaseK8sModel):
    """CustomResourceValidation is a list of validation methods for CustomResources."""

    open_apiv_3_schema: JSONSchemaProps | None = Field(
        default=None,
        alias="openAPIV3Schema",
        description="openAPIV3Schema is the OpenAPI v3 schema to use for validation and pruning.",
    )
