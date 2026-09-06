from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class TypedLocalObjectReference(BaseK8sModel):
    """TypedLocalObjectReference contains enough information to let you locate the typed referenced object inside the same namespace."""

    api_group: str | None = Field(
        default=None,
        alias="apiGroup",
        description="APIGroup is the group for the resource being referenced. If APIGroup is not specified, the specified Kind must be in the core API group. For any other third-party types, APIGroup is required.",
    )
    kind: str = Field(
        ..., alias="kind", description="Kind is the type of resource being referenced"
    )
    name: str = Field(
        ..., alias="name", description="Name is the name of resource being referenced"
    )
