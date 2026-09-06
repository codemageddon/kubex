from pydantic import Field

from kubex.k8s.v1_38.scheduling.v1alpha3.topology_constraint import TopologyConstraint
from kubex_core.models.base import BaseK8sModel


class CompositePodGroupSchedulingConstraints(BaseK8sModel):
    """CompositePodGroupSchedulingConstraints defines scheduling constraints (e.g. topology) for a CompositePodGroup."""

    topology: list[TopologyConstraint] | None = Field(
        default=None,
        alias="topology",
        description="topology defines the topology constraints for the composite pod group. Currently only a single topology constraint can be specified. This may change in the future.",
    )
