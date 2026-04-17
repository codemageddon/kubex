from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class MetricTarget(BaseK8sModel):
    """MetricTarget defines the target value, average value, or average utilization of a specific metric"""

    average_utilization: int | None = Field(
        default=None,
        alias="averageUtilization",
        description="averageUtilization is the target value of the average of the resource metric across all relevant pods, represented as a percentage of the requested value of the resource for the pods. Currently only valid for Resource metric source type",
    )
    average_value: str | None = Field(
        default=None,
        alias="averageValue",
        description="averageValue is the target value of the average of the metric across all relevant pods (as a quantity)",
    )
    type_: str = Field(
        ...,
        alias="type",
        description="type represents whether the metric type is Utilization, Value, or AverageValue",
    )
    value: str | None = Field(
        default=None,
        alias="value",
        description="value is the target value of the metric (as a quantity).",
    )
