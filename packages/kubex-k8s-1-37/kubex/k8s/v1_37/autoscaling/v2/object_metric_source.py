from kubex.k8s.v1_37.autoscaling.v2.cross_version_object_reference import (
    CrossVersionObjectReference,
)
from kubex.k8s.v1_37.autoscaling.v2.metric_identifier import MetricIdentifier
from kubex.k8s.v1_37.autoscaling.v2.metric_target import MetricTarget
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class ObjectMetricSource(BaseK8sModel):
    """ObjectMetricSource indicates how to scale on a metric describing a kubernetes object (for example, hits-per-second on an Ingress object)."""

    described_object: CrossVersionObjectReference = Field(
        ...,
        alias="describedObject",
        description="describedObject specifies the descriptions of a object,such as kind,name apiVersion",
    )
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
