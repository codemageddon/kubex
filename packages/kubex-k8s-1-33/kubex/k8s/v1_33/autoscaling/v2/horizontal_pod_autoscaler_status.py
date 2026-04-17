import datetime

from kubex.k8s.v1_33.autoscaling.v2.horizontal_pod_autoscaler_condition import (
    HorizontalPodAutoscalerCondition,
)
from kubex.k8s.v1_33.autoscaling.v2.metric_status import MetricStatus
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class HorizontalPodAutoscalerStatus(BaseK8sModel):
    """HorizontalPodAutoscalerStatus describes the current status of a horizontal pod autoscaler."""

    conditions: list[HorizontalPodAutoscalerCondition] | None = Field(
        default=None,
        alias="conditions",
        description="conditions is the set of conditions required for this autoscaler to scale its target, and indicates whether or not those conditions are met.",
    )
    current_metrics: list[MetricStatus] | None = Field(
        default=None,
        alias="currentMetrics",
        description="currentMetrics is the last read state of the metrics used by this autoscaler.",
    )
    current_replicas: int | None = Field(
        default=None,
        alias="currentReplicas",
        description="currentReplicas is current number of replicas of pods managed by this autoscaler, as last seen by the autoscaler.",
    )
    desired_replicas: int = Field(
        ...,
        alias="desiredReplicas",
        description="desiredReplicas is the desired number of replicas of pods managed by this autoscaler, as last calculated by the autoscaler.",
    )
    last_scale_time: datetime.datetime | None = Field(
        default=None,
        alias="lastScaleTime",
        description="lastScaleTime is the last time the HorizontalPodAutoscaler scaled the number of pods, used by the autoscaler to control how often the number of pods is changed.",
    )
    observed_generation: int | None = Field(
        default=None,
        alias="observedGeneration",
        description="observedGeneration is the most recent generation observed by this autoscaler.",
    )
