from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class ForNode(BaseK8sModel):
    """ForNode provides information about which nodes should consume this endpoint."""

    name: str = Field(
        ..., alias="name", description="name represents the name of the node."
    )
