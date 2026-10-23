from pydantic import Field

from kubex.k8s.v1_37.scheduling.v1alpha3.all_disruption_mode import AllDisruptionMode
from kubex.k8s.v1_37.scheduling.v1alpha3.single_disruption_mode import (
    SingleDisruptionMode,
)
from kubex_core.models.base import BaseK8sModel


class DisruptionMode(BaseK8sModel):
    """DisruptionMode defines how individual entities within a group can be disrupted. Exactly one mode can be set."""

    all: AllDisruptionMode | None = Field(
        default=None,
        alias="all",
        description="all specifies that all children can only be disrupted together.",
    )
    single: SingleDisruptionMode | None = Field(
        default=None,
        alias="single",
        description="single specifies that children can be disrupted independently from each other.",
    )
