from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class Capabilities(BaseK8sModel):
    """Adds and removes POSIX capabilities from running containers."""

    add: list[str] | None = Field(
        default=None,
        alias="add",
        description="add lists the capabilities to add to the container.",
    )
    drop: list[str] | None = Field(
        default=None,
        alias="drop",
        description="drop lists the capabilities to remove from the container.",
    )
