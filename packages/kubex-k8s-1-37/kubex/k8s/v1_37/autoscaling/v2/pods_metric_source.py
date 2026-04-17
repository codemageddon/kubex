from kubex.k8s.v1_37.autoscaling.v2.metric_identifier import MetricIdentifier
from kubex.k8s.v1_37.autoscaling.v2.metric_target import MetricTarget
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class PodsMetricSource(BaseK8sModel):
    """PodsMetricSource indicates how to scale on a metric describing each pod in the current scale target (for example, transactions-processed-per-second). The values will be averaged together before being compared to the target value."""

    metric: MetricIdentifier = Field(
        ...,
        alias="metric",
        description="metric identifies the target metric by name and selector",
    )
    target: MetricTarget = Field(
        ...,
        alias="target",
        description="target specifies the target value for the given metric",
    )
