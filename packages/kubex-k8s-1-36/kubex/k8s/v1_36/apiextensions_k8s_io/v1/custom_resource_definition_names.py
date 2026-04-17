from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class CustomResourceDefinitionNames(BaseK8sModel):
    """CustomResourceDefinitionNames indicates the names to serve this CustomResourceDefinition"""

    categories: list[str] | None = Field(
        default=None,
        alias="categories",
        description="categories is a list of grouped resources this custom resource belongs to (e.g. 'all'). This is published in API discovery documents, and used by clients to support invocations like `kubectl get all`.",
    )
    kind: str = Field(
        ...,
        alias="kind",
        description="kind is the serialized kind of the resource. It is normally CamelCase and singular. Custom resource instances will use this value as the `kind` attribute in API calls.",
    )
    list_kind: str | None = Field(
        default=None,
        alias="listKind",
        description='listKind is the serialized kind of the list for this resource. Defaults to "`kind`List".',
    )
    plural: str = Field(
        ...,
        alias="plural",
        description="plural is the plural name of the resource to serve. The custom resources are served under `/apis/<group>/<version>/.../<plural>`. Must match the name of the CustomResourceDefinition (in the form `<names.plural>.<group>`). Must be all lowercase.",
    )
    short_names: list[str] | None = Field(
        default=None,
        alias="shortNames",
        description="shortNames are short names for the resource, exposed in API discovery documents, and used by clients to support invocations like `kubectl get <shortname>`. It must be all lowercase.",
    )
    singular: str | None = Field(
        default=None,
        alias="singular",
        description="singular is the singular name of the resource. It must be all lowercase. Defaults to lowercased `kind`.",
    )
