from kubex.k8s.v1_32.autoscaling.v2.container_resource_metric_source import (
    ContainerResourceMetricSource,
)
from kubex.k8s.v1_32.autoscaling.v2.external_metric_source import ExternalMetricSource
from kubex.k8s.v1_32.autoscaling.v2.object_metric_source import ObjectMetricSource
from kubex.k8s.v1_32.autoscaling.v2.pods_metric_source import PodsMetricSource
from kubex.k8s.v1_32.autoscaling.v2.resource_metric_source import ResourceMetricSource
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class MetricSpec(BaseK8sModel):
    """MetricSpec specifies how to scale based on a single metric (only `type` and one other matching field should be set at once)."""

    container_resource: ContainerResourceMetricSource | None = Field(
        default=None,
        alias="containerResource",
        description='containerResource refers to a resource metric (such as those specified in requests and limits) known to Kubernetes describing a single container in each pod of the current scale target (e.g. CPU or memory). Such metrics are built in to Kubernetes, and have special scaling options on top of those available to normal per-pod metrics using the "pods" source.',
    )
    external: ExternalMetricSource | None = Field(
        default=None,
        alias="external",
        description="external refers to a global metric that is not associated with any Kubernetes object. It allows autoscaling based on information coming from components running outside of cluster (for example length of queue in cloud messaging service, or QPS from loadbalancer running outside of cluster).",
    )
    object: ObjectMetricSource | None = Field(
        default=None,
        alias="object",
        description="object refers to a metric describing a single kubernetes object (for example, hits-per-second on an Ingress object).",
    )
    pods: PodsMetricSource | None = Field(
        default=None,
        alias="pods",
        description="pods refers to a metric describing each pod in the current scale target (for example, transactions-processed-per-second). The values will be averaged together before being compared to the target value.",
    )
    resource: ResourceMetricSource | None = Field(
        default=None,
        alias="resource",
        description='resource refers to a resource metric (such as those specified in requests and limits) known to Kubernetes describing each pod in the current scale target (e.g. CPU or memory). Such metrics are built in to Kubernetes, and have special scaling options on top of those available to normal per-pod metrics using the "pods" source.',
    )
    type_: str = Field(
        ...,
        alias="type",
        description='type is the type of metric source. It should be one of "ContainerResource", "External", "Object", "Pods" or "Resource", each mapping to a matching field in the object.',
    )
