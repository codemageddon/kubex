from enum import Enum

from pydantic import Field

from kubex.k8s.v1_30.core.v1.node_address import NodeAddress
from kubex_core.models.base import BaseK8sModel


class NodeStatusPhase(str, Enum):
    PENDING = "Pending"
    RUNNING = "Running"
    TERMINATED = "Terminated"


class NodeStatus(BaseK8sModel):
    """NodeStatus is information about the current status of a node."""

    addresses: list[NodeAddress] | None = Field(default=None, alias="addresses")
    phase: NodeStatusPhase | None = Field(
        default=None,
        alias="phase",
        description="NodePhase is the recently observed lifecycle phase of the node.",
    )
