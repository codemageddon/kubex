from pydantic import Field

from kubex_core.models.base import BaseK8sModel


class NodeAllocatableMappedResources(BaseK8sModel):
    """NodeAllocatableMappedResources describes mapped node allocatable resource allocations."""

    name: str = Field(
        ...,
        alias="name",
        description="Name is the name of the resource (e.g., cpu, memory).",
    )
    quantity: str = Field(
        ...,
        alias="quantity",
        description="Quantity is the total node allocatable resource capacity allocated for the claim. This claim's allocated devices is shared by all the containers referencing the claim. Kubelet adds this value to both requests and limits at the pod-level cgroup, and to limits at the container-level cgroup for each container referencing the claim.",
    )
