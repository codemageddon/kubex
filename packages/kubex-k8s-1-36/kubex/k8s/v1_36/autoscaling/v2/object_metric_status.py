from pydantic import Field

from kubex.k8s.v1_36.autoscaling.v2.cross_version_object_reference import (
    CrossVersionObjectReference,
)
from kubex.k8s.v1_36.autoscaling.v2.metric_identifier import MetricIdentifier
from kubex.k8s.v1_36.autoscaling.v2.metric_value_status import MetricValueStatus
from kubex_core.models.base import BaseK8sModel


class ObjectMetricStatus(BaseK8sModel):
    """ObjectMetricStatus indicates the current value of a metric describing a kubernetes object (for example, hits-per-second on an Ingress object)."""

    current: MetricValueStatus = Field(
        ...,
        alias="current",
        description="current contains the current value for the given metric",
    )
    described_object: CrossVersionObjectReference = Field(
        ...,
        alias="describedObject",
        description="DescribedObject specifies the descriptions of a object,such as kind,name apiVersion",
    )
    metric: MetricIdentifier = Field(
        ...,
        alias="metric",
        description="metric identifies the target metric by name and selector",
    )
