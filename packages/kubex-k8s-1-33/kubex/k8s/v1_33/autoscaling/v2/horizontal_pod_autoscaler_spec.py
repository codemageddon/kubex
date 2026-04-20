from pydantic import Field

from kubex.k8s.v1_33.autoscaling.v2.cross_version_object_reference import (
    CrossVersionObjectReference,
)
from kubex.k8s.v1_33.autoscaling.v2.horizontal_pod_autoscaler_behavior import (
    HorizontalPodAutoscalerBehavior,
)
from kubex.k8s.v1_33.autoscaling.v2.metric_spec import MetricSpec
from kubex_core.models.base import BaseK8sModel


class HorizontalPodAutoscalerSpec(BaseK8sModel):
    """HorizontalPodAutoscalerSpec describes the desired functionality of the HorizontalPodAutoscaler."""

    behavior: HorizontalPodAutoscalerBehavior | None = Field(
        default=None,
        alias="behavior",
        description="behavior configures the scaling behavior of the target in both Up and Down directions (scaleUp and scaleDown fields respectively). If not set, the default HPAScalingRules for scale up and scale down are used.",
    )
    max_replicas: int = Field(
        ...,
        alias="maxReplicas",
        description="maxReplicas is the upper limit for the number of replicas to which the autoscaler can scale up. It cannot be less that minReplicas.",
    )
    metrics: list[MetricSpec] | None = Field(
        default=None,
        alias="metrics",
        description="metrics contains the specifications for which to use to calculate the desired replica count (the maximum replica count across all metrics will be used). The desired replica count is calculated multiplying the ratio between the target value and the current value by the current number of pods. Ergo, metrics used must decrease as the pod count is increased, and vice-versa. See the individual metric source types for more information about how each type of metric must respond. If not set, the default metric will be set to 80% average CPU utilization.",
    )
    min_replicas: int | None = Field(
        default=None,
        alias="minReplicas",
        description="minReplicas is the lower limit for the number of replicas to which the autoscaler can scale down. It defaults to 1 pod. minReplicas is allowed to be 0 if the alpha feature gate HPAScaleToZero is enabled and at least one Object or External metric is configured. Scaling is active as long as at least one metric value is available.",
    )
    scale_target_ref: CrossVersionObjectReference = Field(
        ...,
        alias="scaleTargetRef",
        description="scaleTargetRef points to the target resource to scale, and is used to the pods for which metrics should be collected, as well as to actually change the replica count.",
    )
