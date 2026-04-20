from pydantic import Field

from kubex.k8s.v1_36.autoscaling.v2.metric_identifier import MetricIdentifier
from kubex.k8s.v1_36.autoscaling.v2.metric_target import MetricTarget
from kubex_core.models.base import BaseK8sModel


class ExternalMetricSource(BaseK8sModel):
    """ExternalMetricSource indicates how to scale on a metric not associated with any Kubernetes object (for example length of queue in cloud messaging service, or QPS from loadbalancer running outside of cluster)."""

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
