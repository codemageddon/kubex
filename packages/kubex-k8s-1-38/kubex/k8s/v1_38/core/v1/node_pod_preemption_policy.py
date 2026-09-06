from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class NodePodPreemptionPolicy(BaseK8sModel):
    """NodePodPreemptionPolicy defines the node-level policies governing preemption for pods on this node."""

    disable_resize_preemption: list[str] | None = Field(
        default=None,
        alias="disableResizePreemption",
        description="DisableResizePreemption lists the owners (e.g., autoscalers, operators, administrators) that have requested to disable scheduler and Kubelet preemption for in-place pod resize on this node. If this list is non-empty, resize-induced preemption is disabled on this node. This is an alpha field and requires enabling the InPlacePodVerticalScalingSchedulerPreemption feature gate.",
    )
