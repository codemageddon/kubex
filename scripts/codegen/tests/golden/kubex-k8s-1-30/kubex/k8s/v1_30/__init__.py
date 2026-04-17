from kubex.k8s.v1_30.apps_v1 import (
    Deployment,
    DeploymentCondition,
    DeploymentList,
    DeploymentSpec,
    DeploymentStatus,
)
from kubex.k8s.v1_30.core_v1 import Node, NodeAddress, NodeList, NodeStatus

INDEX: tuple[type, ...] = (
    Deployment,
    Node,
)

__all__ = [
    "DeploymentCondition",
    "DeploymentSpec",
    "DeploymentStatus",
    "Deployment",
    "DeploymentList",
    "NodeAddress",
    "NodeStatus",
    "Node",
    "NodeList",
    "INDEX",
]
