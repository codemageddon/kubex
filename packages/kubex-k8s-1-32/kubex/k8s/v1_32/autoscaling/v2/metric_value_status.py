from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class MetricValueStatus(BaseK8sModel):
    """MetricValueStatus holds the current value for a metric"""

    average_utilization: int | None = Field(
        default=None,
        alias="averageUtilization",
        description="currentAverageUtilization is the current value of the average of the resource metric across all relevant pods, represented as a percentage of the requested value of the resource for the pods.",
    )
    average_value: str | None = Field(
        default=None,
        alias="averageValue",
        description="averageValue is the current value of the average of the metric across all relevant pods (as a quantity)",
    )
    value: str | None = Field(
        default=None,
        alias="value",
        description="value is the current value of the metric (as a quantity).",
    )
