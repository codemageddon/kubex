from enum import Enum
from typing import ClassVar, Literal

from kubex_core.models.base import BaseK8sModel
from kubex_core.models.interfaces import ClusterScopedEntity, HasStatusSubresource
from kubex_core.models.list_entity import ListEntity
from kubex_core.models.metadata import ListMetadata
from kubex_core.models.resource_config import ResourceConfig, Scope
from pydantic import Field


class NodeStatusPhase(str, Enum):
    PENDING = "Pending"
    RUNNING = "Running"
    TERMINATED = "Terminated"


class NodeAddress(BaseK8sModel):
    """NodeAddress reports a node address."""

    address: str = Field(..., alias="address")
    internal_ip: str | None = Field(default=None, alias="internalIP")
    pod_ips: list[str] | None = Field(default=None, alias="podIPs")
    some_nice_api: str | None = Field(default=None, alias="someNiceAPI")
    type_: str = Field(..., alias="type")


class NodeStatus(BaseK8sModel):
    """NodeStatus is information about the current status of a node."""

    addresses: list[NodeAddress] | None = Field(default=None, alias="addresses")
    phase: NodeStatusPhase | None = Field(
        default=None,
        alias="phase",
        description="NodePhase is the recently observed lifecycle phase of the node.",
    )


class Node(ClusterScopedEntity, HasStatusSubresource):
    """Node is a worker node in Kubernetes."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["Node"]] = ResourceConfig["Node"](
        version="v1",
        kind="Node",
        group="core",
        plural="nodes",
        scope=Scope.CLUSTER,
    )
    api_version: Literal["v1"] = Field(default="v1", alias="apiVersion")
    kind: Literal["Node"] = Field(default="Node", alias="kind")
    status: NodeStatus | None = Field(default=None, alias="status")


class NodeList(ListEntity[Node]):
    """NodeList is the whole list of all Nodes."""

    api_version: Literal["v1"] = Field(default="v1", alias="apiVersion")
    items: list[Node] = Field(..., alias="items")
    kind: Literal["NodeList"] = Field(default="NodeList", alias="kind")
    metadata: ListMetadata = Field(..., alias="metadata")


Node.__RESOURCE_CONFIG__._list_model = NodeList
