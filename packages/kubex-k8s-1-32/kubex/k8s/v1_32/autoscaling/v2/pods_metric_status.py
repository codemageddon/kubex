from pydantic import Field

from kubex.k8s.v1_32.autoscaling.v2.metric_identifier import MetricIdentifier
from kubex.k8s.v1_32.autoscaling.v2.metric_value_status import MetricValueStatus
from kubex_core.models.base import BaseK8sModel


class PodsMetricStatus(BaseK8sModel):
    """PodsMetricStatus indicates the current value of a metric describing each pod in the current scale target (for example, transactions-processed-per-second)."""

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
