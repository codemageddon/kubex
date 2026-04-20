from pydantic import Field

from kubex.k8s.v1_33.core.v1.node_selector import NodeSelector
from kubex.k8s.v1_33.resource.v1beta2.device_attribute import DeviceAttribute
from kubex.k8s.v1_33.resource.v1beta2.device_capacity import DeviceCapacity
from kubex.k8s.v1_33.resource.v1beta2.device_counter_consumption import (
    DeviceCounterConsumption,
)
from kubex.k8s.v1_33.resource.v1beta2.device_taint import DeviceTaint
from kubex_core.models.base import BaseK8sModel


class Device(BaseK8sModel):
    """Device represents one individual hardware instance that can be selected based on its attributes. Besides the name, exactly one field must be set."""

    all_nodes: bool | None = Field(
        default=None,
        alias="allNodes",
        description="AllNodes indicates that all nodes have access to the device. Must only be set if Spec.PerDeviceNodeSelection is set to true. At most one of NodeName, NodeSelector and AllNodes can be set.",
    )
    attributes: dict[str, DeviceAttribute] | None = Field(
        default=None,
        alias="attributes",
        description="Attributes defines the set of attributes for this device. The name of each attribute must be unique in that set. The maximum number of attributes and capacities combined is 32.",
    )
    capacity: dict[str, DeviceCapacity] | None = Field(
        default=None,
        alias="capacity",
        description="Capacity defines the set of capacities for this device. The name of each capacity must be unique in that set. The maximum number of attributes and capacities combined is 32.",
    )
    consumes_counters: list[DeviceCounterConsumption] | None = Field(
        default=None,
        alias="consumesCounters",
        description="ConsumesCounters defines a list of references to sharedCounters and the set of counters that the device will consume from those counter sets. There can only be a single entry per counterSet. The total number of device counter consumption entries must be <= 32. In addition, the total number in the entire ResourceSlice must be <= 1024 (for example, 64 devices with 16 counters each).",
    )
    name: str = Field(
        ...,
        alias="name",
        description="Name is unique identifier among all devices managed by the driver in the pool. It must be a DNS label.",
    )
    node_name: str | None = Field(
        default=None,
        alias="nodeName",
        description="NodeName identifies the node where the device is available. Must only be set if Spec.PerDeviceNodeSelection is set to true. At most one of NodeName, NodeSelector and AllNodes can be set.",
    )
    node_selector: NodeSelector | None = Field(
        default=None,
        alias="nodeSelector",
        description="NodeSelector defines the nodes where the device is available. Must use exactly one term. Must only be set if Spec.PerDeviceNodeSelection is set to true. At most one of NodeName, NodeSelector and AllNodes can be set.",
    )
    taints: list[DeviceTaint] | None = Field(
        default=None,
        alias="taints",
        description="If specified, these are the driver-defined taints. The maximum number of taints is 4. This is an alpha field and requires enabling the DRADeviceTaints feature gate.",
    )
