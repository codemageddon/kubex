from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class ForZone(BaseK8sModel):
    """ForZone provides information about which zones should consume this endpoint."""

    name: str = Field(
        ..., alias="name", description="name represents the name of the zone."
    )
