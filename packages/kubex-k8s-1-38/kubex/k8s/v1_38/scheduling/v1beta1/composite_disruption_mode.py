from pydantic import Field

from kubex.k8s.v1_38.scheduling.v1beta1.all_composite_disruption_mode import (
    AllCompositeDisruptionMode,
)
from kubex.k8s.v1_38.scheduling.v1beta1.single_composite_disruption_mode import (
    SingleCompositeDisruptionMode,
)
from kubex_core.models.base import BaseK8sModel


class CompositeDisruptionMode(BaseK8sModel):
    """CompositeDisruptionMode defines how individual entities within a composite pod group can be disrupted. Exactly one mode must be set."""

    all: AllCompositeDisruptionMode | None = Field(
        default=None,
        alias="all",
        description="all specifies that all children groups can only be disrupted together.",
    )
    single: SingleCompositeDisruptionMode | None = Field(
        default=None,
        alias="single",
        description="single specifies that children groups can be disrupted independently from each other.",
    )
