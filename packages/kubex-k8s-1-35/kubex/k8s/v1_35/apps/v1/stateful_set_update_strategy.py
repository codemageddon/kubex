from kubex.k8s.v1_35.apps.v1.rolling_update_stateful_set_strategy import (
    RollingUpdateStatefulSetStrategy,
)
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class StatefulSetUpdateStrategy(BaseK8sModel):
    """StatefulSetUpdateStrategy indicates the strategy that the StatefulSet controller will use to perform updates. It includes any additional parameters necessary to perform the update for the indicated strategy."""

    rolling_update: RollingUpdateStatefulSetStrategy | None = Field(
        default=None,
        alias="rollingUpdate",
        description="RollingUpdate is used to communicate parameters when Type is RollingUpdateStatefulSetStrategyType.",
    )
    type_: str | None = Field(
        default=None,
        alias="type",
        description="Type indicates the type of the StatefulSetUpdateStrategy. Default is RollingUpdate.",
    )
