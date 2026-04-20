from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class PodReadinessGate(BaseK8sModel):
    """PodReadinessGate contains the reference to a pod condition"""

    condition_type: str = Field(
        ...,
        alias="conditionType",
        description="ConditionType refers to a condition in the pod's condition list with matching type.",
    )
