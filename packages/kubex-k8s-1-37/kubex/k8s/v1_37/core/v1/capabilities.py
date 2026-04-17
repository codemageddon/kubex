from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class Capabilities(BaseK8sModel):
    """Adds and removes POSIX capabilities from running containers."""

    add: list[str] | None = Field(
        default=None, alias="add", description="Added capabilities"
    )
    drop: list[str] | None = Field(
        default=None, alias="drop", description="Removed capabilities"
    )
