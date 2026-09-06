from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class ForZone(BaseK8sModel):
    """ForZone provides information about which zones should consume this endpoint."""

    name: str = Field(
        ..., alias="name", description="name represents the name of the zone."
    )
