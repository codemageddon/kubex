import datetime

from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class DeviceTaint(BaseK8sModel):
    """The device this taint is attached to has the "effect" on any claim which does not tolerate the taint and, through the claim, to pods using the claim."""

    effect: str = Field(
        ...,
        alias="effect",
        description="The effect of the taint on claims that do not tolerate the taint and through such claims on the pods using them. Valid effects are NoSchedule and NoExecute. PreferNoSchedule as used for nodes is not valid here.",
    )
    key: str = Field(
        ...,
        alias="key",
        description="The taint key to be applied to a device. Must be a label name.",
    )
    time_added: datetime.datetime | None = Field(
        default=None,
        alias="timeAdded",
        description="TimeAdded represents the time at which the taint was added. Added automatically during create or update if not set.",
    )
    value: str | None = Field(
        default=None,
        alias="value",
        description="The taint value corresponding to the taint key. Must be a label value.",
    )
