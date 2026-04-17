import datetime

from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class HorizontalPodAutoscalerStatus(BaseK8sModel):
    """current status of a horizontal pod autoscaler"""

    current_cpu_utilization_percentage: int | None = Field(
        default=None,
        alias="currentCPUUtilizationPercentage",
        description="currentCPUUtilizationPercentage is the current average CPU utilization over all pods, represented as a percentage of requested CPU, e.g. 70 means that an average pod is using now 70% of its requested CPU.",
    )
    current_replicas: int = Field(
        ...,
        alias="currentReplicas",
        description="currentReplicas is the current number of replicas of pods managed by this autoscaler.",
    )
    desired_replicas: int = Field(
        ...,
        alias="desiredReplicas",
        description="desiredReplicas is the desired number of replicas of pods managed by this autoscaler.",
    )
    last_scale_time: datetime.datetime | None = Field(
        default=None,
        alias="lastScaleTime",
        description="lastScaleTime is the last time the HorizontalPodAutoscaler scaled the number of pods; used by the autoscaler to control how often the number of pods is changed.",
    )
    observed_generation: int | None = Field(
        default=None,
        alias="observedGeneration",
        description="observedGeneration is the most recent generation observed by this autoscaler.",
    )
