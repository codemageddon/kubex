from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class ParentReference(BaseK8sModel):
    """ParentReference describes a reference to a parent object."""

    group: str | None = Field(
        default=None,
        alias="group",
        description="group is the group of the object being referenced.",
    )
    name: str = Field(
        ...,
        alias="name",
        description="name is the name of the object being referenced.",
    )
    namespace: str | None = Field(
        default=None,
        alias="namespace",
        description="namespace is the namespace of the object being referenced.",
    )
    resource: str = Field(
        ...,
        alias="resource",
        description="resource is the resource of the object being referenced.",
    )
