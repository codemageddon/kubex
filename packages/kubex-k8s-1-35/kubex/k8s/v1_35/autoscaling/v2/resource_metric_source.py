from pydantic import Field

from kubex.k8s.v1_35.autoscaling.v2.metric_target import MetricTarget
from kubex_core.models.base import BaseK8sModel


class ResourceMetricSource(BaseK8sModel):
    """ResourceMetricSource indicates how to scale on a resource metric known to Kubernetes, as specified in requests and limits, describing each pod in the current scale target (e.g. CPU or memory). The values will be averaged together before being compared to the target. Such metrics are built in to Kubernetes, and have special scaling options on top of those available to normal per-pod metrics using the "pods" source. Only one "target" type should be set."""

    name: str = Field(
        ..., alias="name", description="name is the name of the resource in question."
    )
    target: MetricTarget = Field(
        ...,
        alias="target",
        description="target specifies the target value for the given metric",
    )
