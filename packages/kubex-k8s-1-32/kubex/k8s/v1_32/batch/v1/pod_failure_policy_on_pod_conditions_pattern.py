from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class PodFailurePolicyOnPodConditionsPattern(BaseK8sModel):
    """PodFailurePolicyOnPodConditionsPattern describes a pattern for matching an actual pod condition type."""

    status: str = Field(
        ...,
        alias="status",
        description="Specifies the required Pod condition status. To match a pod condition it is required that the specified status equals the pod condition status. Defaults to True.",
    )
    type_: str = Field(
        ...,
        alias="type",
        description="Specifies the required Pod condition type. To match a pod condition it is required that specified type equals the pod condition type.",
    )
