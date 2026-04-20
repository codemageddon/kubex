from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class TypedLocalObjectReference(BaseK8sModel):
    """TypedLocalObjectReference allows to reference typed object inside the same namespace."""

    api_group: str | None = Field(
        default=None,
        alias="apiGroup",
        description="APIGroup is the group for the resource being referenced. If APIGroup is empty, the specified Kind must be in the core API group. For any other third-party types, setting APIGroup is required. It must be a DNS subdomain.",
    )
    kind: str = Field(
        ...,
        alias="kind",
        description="Kind is the type of resource being referenced. It must be a path segment name.",
    )
    name: str = Field(
        ...,
        alias="name",
        description="Name is the name of resource being referenced. It must be a path segment name.",
    )
