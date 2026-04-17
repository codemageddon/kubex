from kubex.k8s.v1_32.autoscaling.v1.cross_version_object_reference import (
    CrossVersionObjectReference,
)
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class HorizontalPodAutoscalerSpec(BaseK8sModel):
    """specification of a horizontal pod autoscaler."""

    max_replicas: int = Field(
        ...,
        alias="maxReplicas",
        description="maxReplicas is the upper limit for the number of pods that can be set by the autoscaler; cannot be smaller than MinReplicas.",
    )
    min_replicas: int | None = Field(
        default=None,
        alias="minReplicas",
        description="minReplicas is the lower limit for the number of replicas to which the autoscaler can scale down. It defaults to 1 pod. minReplicas is allowed to be 0 if the alpha feature gate HPAScaleToZero is enabled and at least one Object or External metric is configured. Scaling is active as long as at least one metric value is available.",
    )
    scale_target_ref: CrossVersionObjectReference = Field(
        ...,
        alias="scaleTargetRef",
        description="reference to scaled resource; horizontal pod autoscaler will learn the current resource consumption and will set the desired number of pods by using its Scale subresource.",
    )
    target_cpu_utilization_percentage: int | None = Field(
        default=None,
        alias="targetCPUUtilizationPercentage",
        description="targetCPUUtilizationPercentage is the target average CPU utilization (represented as a percentage of requested CPU) over all the pods; if not specified the default autoscaling policy will be used.",
    )
