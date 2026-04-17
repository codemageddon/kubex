from kubex.k8s.v1_35.flowcontrol.v1.priority_level_configuration_condition import (
    PriorityLevelConfigurationCondition,
)
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class PriorityLevelConfigurationStatus(BaseK8sModel):
    """PriorityLevelConfigurationStatus represents the current state of a "request-priority"."""

    conditions: list[PriorityLevelConfigurationCondition] | None = Field(
        default=None,
        alias="conditions",
        description='`conditions` is the current state of "request-priority".',
    )
