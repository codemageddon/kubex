from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class PodSchedulingGate(BaseK8sModel):
    """PodSchedulingGate is associated to a Pod to guard its scheduling."""

    name: str = Field(
        ...,
        alias="name",
        description="Name of the scheduling gate. Each scheduling gate must have a unique name field.",
    )
