from pydantic import Field

from kubex.k8s.v1_36.apiextensions_k8s_io.v1.custom_resource_column_definition import (
    CustomResourceColumnDefinition,
)
from kubex.k8s.v1_36.apiextensions_k8s_io.v1.custom_resource_subresources import (
    CustomResourceSubresources,
)
from kubex.k8s.v1_36.apiextensions_k8s_io.v1.custom_resource_validation import (
    CustomResourceValidation,
)
from kubex.k8s.v1_36.apiextensions_k8s_io.v1.selectable_field import SelectableField
from kubex_core.models.base import BaseK8sModel


class CustomResourceDefinitionVersion(BaseK8sModel):
    """CustomResourceDefinitionVersion describes a version for CRD."""

    additional_printer_columns: list[CustomResourceColumnDefinition] | None = Field(
        default=None,
        alias="additionalPrinterColumns",
        description="additionalPrinterColumns specifies additional columns returned in Table output. See https://kubernetes.io/docs/reference/using-api/api-concepts/#receiving-resources-as-tables for details. If no columns are specified, a single column displaying the age of the custom resource is used.",
    )
    deprecated: bool | None = Field(
        default=None,
        alias="deprecated",
        description="deprecated indicates this version of the custom resource API is deprecated. When set to true, API requests to this version receive a warning header in the server response. Defaults to false.",
    )
    deprecation_warning: str | None = Field(
        default=None,
        alias="deprecationWarning",
        description="deprecationWarning overrides the default warning returned to API clients. May only be set when `deprecated` is true. The default warning indicates this version is deprecated and recommends use of the newest served version of equal or greater stability, if one exists.",
    )
    name: str = Field(
        ...,
        alias="name",
        description="name is the version name, e.g. “v1”, “v2beta1”, etc. The custom resources are served under this version at `/apis/<group>/<version>/...` if `served` is true.",
    )
    schema_: CustomResourceValidation | None = Field(
        default=None,
        alias="schema",
        description="schema describes the schema used for validation, pruning, and defaulting of this version of the custom resource.",
    )
    selectable_fields: list[SelectableField] | None = Field(
        default=None,
        alias="selectableFields",
        description="selectableFields specifies paths to fields that may be used as field selectors. A maximum of 8 selectable fields are allowed. See https://kubernetes.io/docs/concepts/overview/working-with-objects/field-selectors",
    )
    served: bool = Field(
        ...,
        alias="served",
        description="served is a flag enabling/disabling this version from being served via REST APIs",
    )
    storage: bool = Field(
        ...,
        alias="storage",
        description="storage indicates this version should be used when persisting custom resources to storage. There must be exactly one version with storage=true.",
    )
    subresources: CustomResourceSubresources | None = Field(
        default=None,
        alias="subresources",
        description="subresources specify what subresources this version of the defined custom resource have.",
    )
