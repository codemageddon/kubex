from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class GroupVersionResource(BaseK8sModel):
    """The names of the group, the version, and the resource."""

    group: str | None = Field(
        default=None, alias="group", description="The name of the group."
    )
    resource: str | None = Field(
        default=None, alias="resource", description="The name of the resource."
    )
    version: str | None = Field(
        default=None, alias="version", description="The name of the version."
    )
