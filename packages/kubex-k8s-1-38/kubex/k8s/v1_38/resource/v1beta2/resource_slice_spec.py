from pydantic import Field

from kubex.k8s.v1_38.core.v1.node_selector import NodeSelector
from kubex.k8s.v1_38.resource.v1beta2.counter_set import CounterSet
from kubex.k8s.v1_38.resource.v1beta2.device import Device
from kubex.k8s.v1_38.resource.v1beta2.resource_pool import ResourcePool
from kubex_core.models.base import BaseK8sModel


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
        description="Devices lists some or all of the devices in this pool. Must not have more than 128 entries. If any device uses taints or consumes counters the limit is 64. Only one of Devices and SharedCounters can be set in a ResourceSlice.",
    )
    driver: str = Field(
        ...,
        alias="driver",
        description="Driver identifies the DRA driver providing the capacity information. A field selector can be used to list only ResourceSlice objects with a certain driver name. Must be a DNS subdomain and should end with a DNS domain owned by the vendor of the driver. It should use only lower case characters. This field is immutable.",
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
    partition_type_attribute: str | None = Field(
        default=None,
        alias="partitionTypeAttribute",
        description='PartitionTypeAttribute names a string device attribute (by fully qualified name, e.g. "gpu.example.com/profile") whose value labels each device with its partition type, such as "Full" or "Half" for a MIG-style GPU. When set, every partitionable device in the slice must carry the attribute and devices sharing a value must share the same ConsumesCounters cost.',
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
        description="SharedCounters defines a list of counter sets, each of which has a name and a list of counters available. The names of the counter sets must be unique in the ResourcePool. Only one of Devices and SharedCounters can be set in a ResourceSlice. The maximum number of counter sets is 8.",
    )
    skip_node_operations: list[str] | None = Field(
        default=None,
        alias="skipNodeOperations",
        description='SkipNodeOperations lists node-local resource operations (gRPC calls) that will be skipped for the devices in this slice when determining whether operations are necessary on the node. If all allocated devices for a driver in a claim skip an operation, that gRPC call will be skipped. Valid values are: - "NodePrepareResources": NodePrepareResources gRPC calls are skipped. This value cannot be specified unless "NodeUnprepareResources" is also listed (or "*" is specified). - "NodeUnprepareResources": NodeUnprepareResources gRPC calls are skipped. - "*": All node-local resource operations are skipped. Other values may be added in the future. The kubelet must ignore unknown values.',
    )
