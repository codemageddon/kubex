import datetime

from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class PodCondition(BaseK8sModel):
    """PodCondition contains details for the current condition of this pod."""

    last_probe_time: datetime.datetime | None = Field(
        default=None,
        alias="lastProbeTime",
        description="Last time we probed the condition.",
    )
    last_transition_time: datetime.datetime | None = Field(
        default=None,
        alias="lastTransitionTime",
        description="Last time the condition transitioned from one status to another.",
    )
    message: str | None = Field(
        default=None,
        alias="message",
        description="Human-readable message indicating details about last transition.",
    )
    observed_generation: int | None = Field(
        default=None,
        alias="observedGeneration",
        description="If set, this represents the .metadata.generation that the pod condition was set based upon. This is an alpha field. Enable PodObservedGenerationTracking to be able to use this field.",
    )
    reason: str | None = Field(
        default=None,
        alias="reason",
        description="Unique, one-word, CamelCase reason for the condition's last transition.",
    )
    status: str = Field(
        ...,
        alias="status",
        description="Status is the status of the condition. Can be True, False, Unknown. More info: https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle#pod-conditions",
    )
    type_: str = Field(
        ...,
        alias="type",
        description="Type is the type of the condition. More info: https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle#pod-conditions",
    )
