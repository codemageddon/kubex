import datetime

from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class PersistentVolumeClaimCondition(BaseK8sModel):
    """PersistentVolumeClaimCondition contains details about state of pvc"""

    last_probe_time: datetime.datetime | None = Field(
        default=None,
        alias="lastProbeTime",
        description="lastProbeTime is the time we probed the condition.",
    )
    last_transition_time: datetime.datetime | None = Field(
        default=None,
        alias="lastTransitionTime",
        description="lastTransitionTime is the time the condition transitioned from one status to another.",
    )
    message: str | None = Field(
        default=None,
        alias="message",
        description="message is the human-readable message indicating details about last transition.",
    )
    reason: str | None = Field(
        default=None,
        alias="reason",
        description='reason is a unique, this should be a short, machine understandable string that gives the reason for condition\'s last transition. If it reports "Resizing" that means the underlying persistent volume is being resized.',
    )
    status: str = Field(
        ...,
        alias="status",
        description="Status is the status of the condition. Can be True, False, Unknown. More info: https://kubernetes.io/docs/reference/kubernetes-api/config-and-storage-resources/persistent-volume-claim-v1/#:~:text=state%20of%20pvc-,conditions.status,-(string)%2C%20required",
    )
    type_: str = Field(
        ...,
        alias="type",
        description="Type is the type of the condition. More info: https://kubernetes.io/docs/reference/kubernetes-api/config-and-storage-resources/persistent-volume-claim-v1/#:~:text=set%20to%20%27ResizeStarted%27.-,PersistentVolumeClaimCondition,-contains%20details%20about",
    )
