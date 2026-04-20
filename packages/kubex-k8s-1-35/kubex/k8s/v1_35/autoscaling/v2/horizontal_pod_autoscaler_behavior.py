from pydantic import Field

from kubex.k8s.v1_35.autoscaling.v2.hpa_scaling_rules import HPAScalingRules
from kubex_core.models.base import BaseK8sModel


class HorizontalPodAutoscalerBehavior(BaseK8sModel):
    """HorizontalPodAutoscalerBehavior configures the scaling behavior of the target in both Up and Down directions (scaleUp and scaleDown fields respectively)."""

    scale_down: HPAScalingRules | None = Field(
        default=None,
        alias="scaleDown",
        description="scaleDown is scaling policy for scaling Down. If not set, the default value is to allow to scale down to minReplicas pods, with a 300 second stabilization window (i.e., the highest recommendation for the last 300sec is used).",
    )
    scale_up: HPAScalingRules | None = Field(
        default=None,
        alias="scaleUp",
        description="scaleUp is scaling policy for scaling Up. If not set, the default value is the higher of: * increase no more than 4 pods per 60 seconds * double the number of pods per 60 seconds No stabilization is used.",
    )
