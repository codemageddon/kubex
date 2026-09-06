from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class ForNode(BaseK8sModel):
    """ForNode provides information about which nodes should consume this endpoint."""

    name: str = Field(
        ..., alias="name", description="name represents the name of the node."
    )
