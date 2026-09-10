from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class HPAScalingPolicy(BaseK8sModel):
    """HPAScalingPolicy is a single policy which must hold true for a specified past interval."""

    period_seconds: int = Field(
        ...,
        alias="periodSeconds",
        description="periodSeconds specifies the window of time for which the policy should hold true. PeriodSeconds must be greater than zero and less than or equal to 1800 (30 min).",
    )
    type_: str = Field(
        ..., alias="type", description="type is used to specify the scaling policy."
    )
    value: int = Field(
        ...,
        alias="value",
        description="value contains the amount of change which is permitted by the policy. It must be greater than zero",
    )
