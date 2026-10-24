from pydantic import Field

from kubex_core.models.base import BaseK8sModel
from kubex_core.models.types import Time


class PodCondition(BaseK8sModel):
    """PodCondition contains details for the current condition of this pod."""

    last_probe_time: Time | None = Field(
        default=None,
        alias="lastProbeTime",
        description="lastProbeTime is the last time we probed the condition.",
    )
    last_transition_time: Time | None = Field(
        default=None,
        alias="lastTransitionTime",
        description="lastTransitionTime is the last time the condition transitioned from one status to another.",
    )
    message: str | None = Field(
        default=None,
        alias="message",
        description="message is a human-readable message indicating details about last transition.",
    )
    observed_generation: int | None = Field(
        default=None,
        alias="observedGeneration",
        description="observedGeneration if set, this represents the .metadata.generation that the pod condition was set based upon.",
    )
    reason: str | None = Field(
        default=None,
        alias="reason",
        description="reason is the unique, one-word, CamelCase reason for the condition's last transition.",
    )
    status: str = Field(
        ...,
        alias="status",
        description="status is the status of the condition. Can be True, False, Unknown. More info: https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle#pod-conditions",
    )
    type_: str = Field(
        ...,
        alias="type",
        description="type is the type of the condition. More info: https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle#pod-conditions",
    )
