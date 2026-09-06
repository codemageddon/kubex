from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class RoleRef(BaseK8sModel):
    """RoleRef contains information that points to the role being used"""

    api_group: str | None = Field(
        default=None,
        alias="apiGroup",
        description="apiGroup is the group for the resource being referenced",
    )
    kind: str = Field(
        ..., alias="kind", description="kind is the type of resource being referenced"
    )
    name: str = Field(
        ..., alias="name", description="name is the name of resource being referenced"
    )
