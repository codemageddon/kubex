from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class PriorityLevelConfigurationReference(BaseK8sModel):
    """PriorityLevelConfigurationReference contains information that points to the "request-priority" being used."""

    name: str = Field(
        ...,
        alias="name",
        description="`name` is the name of the priority level configuration being referenced Required.",
    )
