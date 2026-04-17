from kubex.k8s.v1_37.autoscaling.v2.metric_identifier import MetricIdentifier
from kubex.k8s.v1_37.autoscaling.v2.metric_value_status import MetricValueStatus
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class ExternalMetricStatus(BaseK8sModel):
    """ExternalMetricStatus indicates the current value of a global metric not associated with any Kubernetes object."""

    current: MetricValueStatus = Field(
        ...,
        alias="current",
        description="current contains the current value for the given metric",
    )
    metric: MetricIdentifier = Field(
        ...,
        alias="metric",
        description="metric identifies the target metric by name and selector",
    )
