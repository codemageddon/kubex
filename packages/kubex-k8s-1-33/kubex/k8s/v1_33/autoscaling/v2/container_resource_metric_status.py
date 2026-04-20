from pydantic import Field

from kubex.k8s.v1_33.autoscaling.v2.metric_value_status import MetricValueStatus
from kubex_core.models.base import BaseK8sModel


class ContainerResourceMetricStatus(BaseK8sModel):
    """ContainerResourceMetricStatus indicates the current value of a resource metric known to Kubernetes, as specified in requests and limits, describing a single container in each pod in the current scale target (e.g. CPU or memory). Such metrics are built in to Kubernetes, and have special scaling options on top of those available to normal per-pod metrics using the "pods" source."""

    container: str = Field(
        ...,
        alias="container",
        description="container is the name of the container in the pods of the scaling target",
    )
    current: MetricValueStatus = Field(
        ...,
        alias="current",
        description="current contains the current value for the given metric",
    )
    name: str = Field(
        ..., alias="name", description="name is the name of the resource in question."
    )
