import datetime

from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class PersistentVolumeStatus(BaseK8sModel):
    """PersistentVolumeStatus is the current status of a persistent volume."""

    last_phase_transition_time: datetime.datetime | None = Field(
        default=None,
        alias="lastPhaseTransitionTime",
        description="lastPhaseTransitionTime is the time the phase transitioned from one to another and automatically resets to current time everytime a volume phase transitions.",
    )
    message: str | None = Field(
        default=None,
        alias="message",
        description="message is a human-readable message indicating details about why the volume is in this state.",
    )
    phase: str | None = Field(
        default=None,
        alias="phase",
        description="phase indicates if a volume is available, bound to a claim, or released by a claim. More info: https://kubernetes.io/docs/concepts/storage/persistent-volumes#phase",
    )
    reason: str | None = Field(
        default=None,
        alias="reason",
        description="reason is a brief CamelCase string that describes any failure and is meant for machine parsing and tidy display in the CLI.",
    )
