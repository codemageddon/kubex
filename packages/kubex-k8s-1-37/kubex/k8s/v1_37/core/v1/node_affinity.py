from pydantic import Field

from kubex.k8s.v1_37.core.v1.node_selector import NodeSelector
from kubex.k8s.v1_37.core.v1.preferred_scheduling_term import PreferredSchedulingTerm
from kubex_core.models.base import BaseK8sModel


class NodeAffinity(BaseK8sModel):
    """Node affinity is a group of node affinity scheduling rules."""

    preferred_during_scheduling_ignored_during_execution: (
        list[PreferredSchedulingTerm] | None
    ) = Field(
        default=None,
        alias="preferredDuringSchedulingIgnoredDuringExecution",
        description='The scheduler will prefer to schedule pods to nodes that satisfy the affinity expressions specified by this field, but it may choose a node that violates one or more of the expressions. The node that is most preferred is the one with the greatest sum of weights, i.e. for each node that meets all of the scheduling requirements (resource request, requiredDuringScheduling affinity expressions, etc.), compute a sum by iterating through the elements of this field and adding "weight" to the sum if the node matches the corresponding matchExpressions; the node(s) with the highest sum are the most preferred.',
    )
    required_during_scheduling_ignored_during_execution: NodeSelector | None = Field(
        default=None,
        alias="requiredDuringSchedulingIgnoredDuringExecution",
        description="If the affinity requirements specified by this field are not met at scheduling time, the pod will not be scheduled onto the node. If the affinity requirements specified by this field cease to be met at some point during pod execution (e.g. due to an update), the system may or may not try to eventually evict the pod from its node.",
    )
