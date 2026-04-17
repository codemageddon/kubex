from kubex.k8s.v1_35.autoscaling.v2.container_resource_metric_status import (
    ContainerResourceMetricStatus,
)
from kubex.k8s.v1_35.autoscaling.v2.external_metric_status import ExternalMetricStatus
from kubex.k8s.v1_35.autoscaling.v2.object_metric_status import ObjectMetricStatus
from kubex.k8s.v1_35.autoscaling.v2.pods_metric_status import PodsMetricStatus
from kubex.k8s.v1_35.autoscaling.v2.resource_metric_status import ResourceMetricStatus
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class MetricStatus(BaseK8sModel):
    """MetricStatus describes the last-read state of a single metric."""

    container_resource: ContainerResourceMetricStatus | None = Field(
        default=None,
        alias="containerResource",
        description='container resource refers to a resource metric (such as those specified in requests and limits) known to Kubernetes describing a single container in each pod in the current scale target (e.g. CPU or memory). Such metrics are built in to Kubernetes, and have special scaling options on top of those available to normal per-pod metrics using the "pods" source.',
    )
    external: ExternalMetricStatus | None = Field(
        default=None,
        alias="external",
        description="external refers to a global metric that is not associated with any Kubernetes object. It allows autoscaling based on information coming from components running outside of cluster (for example length of queue in cloud messaging service, or QPS from loadbalancer running outside of cluster).",
    )
    object: ObjectMetricStatus | None = Field(
        default=None,
        alias="object",
        description="object refers to a metric describing a single kubernetes object (for example, hits-per-second on an Ingress object).",
    )
    pods: PodsMetricStatus | None = Field(
        default=None,
        alias="pods",
        description="pods refers to a metric describing each pod in the current scale target (for example, transactions-processed-per-second). The values will be averaged together before being compared to the target value.",
    )
    resource: ResourceMetricStatus | None = Field(
        default=None,
        alias="resource",
        description='resource refers to a resource metric (such as those specified in requests and limits) known to Kubernetes describing each pod in the current scale target (e.g. CPU or memory). Such metrics are built in to Kubernetes, and have special scaling options on top of those available to normal per-pod metrics using the "pods" source.',
    )
    type_: str = Field(
        ...,
        alias="type",
        description='type is the type of metric source. It will be one of "ContainerResource", "External", "Object", "Pods" or "Resource", each corresponds to a matching field in the object.',
    )
