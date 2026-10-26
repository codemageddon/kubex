from pydantic import Field

from kubex_core.models.base import BaseK8sModel
from kubex_core.models.types import Time


class Taint(BaseK8sModel):
    """The node this Taint is attached to has the \"effect\" on any pod that does not tolerate the Taint."""

    effect: str = Field(
        ...,
        alias="effect",
        description="effect is the effect of the taint on pods that do not tolerate the taint. Required. Valid effects are NoSchedule, PreferNoSchedule and NoExecute.",
    )
    key: str = Field(
        ...,
        alias="key",
        description="key is the taint key to be applied to a node. Required. The taint key to be applied to a node.",
    )
    time_added: Time | None = Field(
        default=None,
        alias="timeAdded",
        description="timeAdded represents the time at which the taint was added.",
    )
    value: str | None = Field(
        default=None,
        alias="value",
        description="value is the taint value corresponding to the taint key.",
    )
