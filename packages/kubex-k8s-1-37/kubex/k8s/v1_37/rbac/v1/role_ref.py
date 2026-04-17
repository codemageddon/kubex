from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class RoleRef(BaseK8sModel):
    """RoleRef contains information that points to the role being used"""

    api_group: str | None = Field(
        default=None,
        alias="apiGroup",
        description="APIGroup is the group for the resource being referenced",
    )
    kind: str = Field(
        ..., alias="kind", description="Kind is the type of resource being referenced"
    )
    name: str = Field(
        ..., alias="name", description="Name is the name of resource being referenced"
    )
