from pydantic import Field

from kubex.k8s.v1_37.scheduling.v1alpha3.topology_constraint import TopologyConstraint
from kubex_core.models.base import BaseK8sModel


class WorkloadPodGroupSchedulingConstraints(BaseK8sModel):
    """WorkloadPodGroupSchedulingConstraints defines leaf-level scheduling constraints, such as topology."""

    topology: list[TopologyConstraint] | None = Field(
        default=None,
        alias="topology",
        description="topology specifies desired topological placements for all pods within the pod group. If unset, no topology placement is requested.",
    )
