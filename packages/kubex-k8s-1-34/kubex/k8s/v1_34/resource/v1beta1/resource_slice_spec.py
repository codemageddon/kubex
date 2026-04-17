from kubex.k8s.v1_34.core.v1.node_selector import NodeSelector
from kubex.k8s.v1_34.resource.v1beta1.counter_set import CounterSet
from kubex.k8s.v1_34.resource.v1beta1.device import Device
from kubex.k8s.v1_34.resource.v1beta1.resource_pool import ResourcePool
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class ResourceSliceSpec(BaseK8sModel):
    """ResourceSliceSpec contains the information published by the driver in one ResourceSlice."""

    all_nodes: bool | None = Field(
        default=None,
        alias="allNodes",
        description="AllNodes indicates that all nodes have access to the resources in the pool. Exactly one of NodeName, NodeSelector, AllNodes, and PerDeviceNodeSelection must be set.",
    )
    devices: list[Device] | None = Field(
        default=None,
        alias="devices",
        description="Devices lists some or all of the devices in this pool. Must not have more than 128 entries.",
    )
    driver: str = Field(
        ...,
        alias="driver",
        description="Driver identifies the DRA driver providing the capacity information. A field selector can be used to list only ResourceSlice objects with a certain driver name. Must be a DNS subdomain and should end with a DNS domain owned by the vendor of the driver. This field is immutable.",
    )
    node_name: str | None = Field(
        default=None,
        alias="nodeName",
        description="NodeName identifies the node which provides the resources in this pool. A field selector can be used to list only ResourceSlice objects belonging to a certain node. This field can be used to limit access from nodes to ResourceSlices with the same node name. It also indicates to autoscalers that adding new nodes of the same type as some old node might also make new resources available. Exactly one of NodeName, NodeSelector, AllNodes, and PerDeviceNodeSelection must be set. This field is immutable.",
    )
    node_selector: NodeSelector | None = Field(
        default=None,
        alias="nodeSelector",
        description="NodeSelector defines which nodes have access to the resources in the pool, when that pool is not limited to a single node. Must use exactly one term. Exactly one of NodeName, NodeSelector, AllNodes, and PerDeviceNodeSelection must be set.",
    )
    per_device_node_selection: bool | None = Field(
        default=None,
        alias="perDeviceNodeSelection",
        description="PerDeviceNodeSelection defines whether the access from nodes to resources in the pool is set on the ResourceSlice level or on each device. If it is set to true, every device defined the ResourceSlice must specify this individually. Exactly one of NodeName, NodeSelector, AllNodes, and PerDeviceNodeSelection must be set.",
    )
    pool: ResourcePool = Field(
        ...,
        alias="pool",
        description="Pool describes the pool that this ResourceSlice belongs to.",
    )
    shared_counters: list[CounterSet] | None = Field(
        default=None,
        alias="sharedCounters",
        description="SharedCounters defines a list of counter sets, each of which has a name and a list of counters available. The names of the SharedCounters must be unique in the ResourceSlice. The maximum number of SharedCounters is 32.",
    )
