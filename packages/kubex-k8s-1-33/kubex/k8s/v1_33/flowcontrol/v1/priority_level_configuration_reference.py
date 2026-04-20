from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class PriorityLevelConfigurationReference(BaseK8sModel):
    """PriorityLevelConfigurationReference contains information that points to the "request-priority" being used."""

    name: str = Field(
        ...,
        alias="name",
        description="`name` is the name of the priority level configuration being referenced Required.",
    )
