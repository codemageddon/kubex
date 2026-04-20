from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class IngressClassParametersReference(BaseK8sModel):
    """IngressClassParametersReference identifies an API object. This can be used to specify a cluster or namespace-scoped resource."""

    api_group: str | None = Field(
        default=None,
        alias="apiGroup",
        description="apiGroup is the group for the resource being referenced. If APIGroup is not specified, the specified Kind must be in the core API group. For any other third-party types, APIGroup is required.",
    )
    kind: str = Field(
        ..., alias="kind", description="kind is the type of resource being referenced."
    )
    name: str = Field(
        ..., alias="name", description="name is the name of resource being referenced."
    )
    namespace: str | None = Field(
        default=None,
        alias="namespace",
        description='namespace is the namespace of the resource being referenced. This field is required when scope is set to "Namespace" and must be unset when scope is set to "Cluster".',
    )
    scope: str | None = Field(
        default=None,
        alias="scope",
        description='scope represents if this refers to a cluster or namespace scoped resource. This may be set to "Cluster" (default) or "Namespace".',
    )
