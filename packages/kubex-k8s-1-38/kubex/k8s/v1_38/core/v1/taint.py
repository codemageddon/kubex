import datetime

from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class Taint(BaseK8sModel):
    """The node this Taint is attached to has the "effect" on any pod that does not tolerate the Taint."""

    effect: str = Field(
        ...,
        alias="effect",
        description="Required. The effect of the taint on pods that do not tolerate the taint. Valid effects are NoSchedule, PreferNoSchedule and NoExecute.",
    )
    key: str = Field(
        ..., alias="key", description="Required. The taint key to be applied to a node."
    )
    time_added: datetime.datetime | None = Field(
        default=None,
        alias="timeAdded",
        description="TimeAdded represents the time at which the taint was added.",
    )
    value: str | None = Field(
        default=None,
        alias="value",
        description="The taint value corresponding to the taint key.",
    )
