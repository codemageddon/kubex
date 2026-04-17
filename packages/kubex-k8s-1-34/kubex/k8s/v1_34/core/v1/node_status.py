from kubex.k8s.v1_34.core.v1.attached_volume import AttachedVolume
from kubex.k8s.v1_34.core.v1.container_image import ContainerImage
from kubex.k8s.v1_34.core.v1.node_address import NodeAddress
from kubex.k8s.v1_34.core.v1.node_condition import NodeCondition
from kubex.k8s.v1_34.core.v1.node_config_status import NodeConfigStatus
from kubex.k8s.v1_34.core.v1.node_daemon_endpoints import NodeDaemonEndpoints
from kubex.k8s.v1_34.core.v1.node_features import NodeFeatures
from kubex.k8s.v1_34.core.v1.node_runtime_handler import NodeRuntimeHandler
from kubex.k8s.v1_34.core.v1.node_system_info import NodeSystemInfo
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class NodeStatus(BaseK8sModel):
    """NodeStatus is information about the current status of a node."""

    addresses: list[NodeAddress] | None = Field(
        default=None,
        alias="addresses",
        description="List of addresses reachable to the node. Queried from cloud provider, if available. More info: https://kubernetes.io/docs/reference/node/node-status/#addresses Note: This field is declared as mergeable, but the merge key is not sufficiently unique, which can cause data corruption when it is merged. Callers should instead use a full-replacement patch. See https://pr.k8s.io/79391 for an example. Consumers should assume that addresses can change during the lifetime of a Node. However, there are some exceptions where this may not be possible, such as Pods that inherit a Node's address in its own status or consumers of the downward API (status.hostIP).",
    )
    allocatable: dict[str, str] | None = Field(
        default=None,
        alias="allocatable",
        description="Allocatable represents the resources of a node that are available for scheduling. Defaults to Capacity.",
    )
    capacity: dict[str, str] | None = Field(
        default=None,
        alias="capacity",
        description="Capacity represents the total resources of a node. More info: https://kubernetes.io/docs/reference/node/node-status/#capacity",
    )
    conditions: list[NodeCondition] | None = Field(
        default=None,
        alias="conditions",
        description="Conditions is an array of current observed node conditions. More info: https://kubernetes.io/docs/reference/node/node-status/#condition",
    )
    config: NodeConfigStatus | None = Field(
        default=None,
        alias="config",
        description="Status of the config assigned to the node via the dynamic Kubelet config feature.",
    )
    daemon_endpoints: NodeDaemonEndpoints | None = Field(
        default=None,
        alias="daemonEndpoints",
        description="Endpoints of daemons running on the Node.",
    )
    features: NodeFeatures | None = Field(
        default=None,
        alias="features",
        description="Features describes the set of features implemented by the CRI implementation.",
    )
    images: list[ContainerImage] | None = Field(
        default=None,
        alias="images",
        description="List of container images on this node",
    )
    node_info: NodeSystemInfo | None = Field(
        default=None,
        alias="nodeInfo",
        description="Set of ids/uuids to uniquely identify the node. More info: https://kubernetes.io/docs/reference/node/node-status/#info",
    )
    phase: str | None = Field(
        default=None,
        alias="phase",
        description="NodePhase is the recently observed lifecycle phase of the node. More info: https://kubernetes.io/docs/concepts/nodes/node/#phase The field is never populated, and now is deprecated.",
    )
    runtime_handlers: list[NodeRuntimeHandler] | None = Field(
        default=None,
        alias="runtimeHandlers",
        description="The available runtime handlers.",
    )
    volumes_attached: list[AttachedVolume] | None = Field(
        default=None,
        alias="volumesAttached",
        description="List of volumes that are attached to the node.",
    )
    volumes_in_use: list[str] | None = Field(
        default=None,
        alias="volumesInUse",
        description="List of attachable volumes in use (mounted) by the node.",
    )
