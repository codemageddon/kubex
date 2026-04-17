from kubex.k8s.v1_37.scheduling.v1alpha2.topology_constraint import TopologyConstraint
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class PodGroupSchedulingConstraints(BaseK8sModel):
    """PodGroupSchedulingConstraints defines scheduling constraints (e.g. topology) for a PodGroup."""

    topology: list[TopologyConstraint] | None = Field(
        default=None,
        alias="topology",
        description="Topology defines the topology constraints for the pod group. Currently only a single topology constraint can be specified. This may change in the future.",
    )
