from kubex.k8s.v1_35.core.v1.node_selector import NodeSelector
from kubex.k8s.v1_35.resource.v1.device_attribute import DeviceAttribute
from kubex.k8s.v1_35.resource.v1.device_capacity import DeviceCapacity
from kubex.k8s.v1_35.resource.v1.device_counter_consumption import (
    DeviceCounterConsumption,
)
from kubex.k8s.v1_35.resource.v1.device_taint import DeviceTaint
from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class Device(BaseK8sModel):
    """Device represents one individual hardware instance that can be selected based on its attributes. Besides the name, exactly one field must be set."""

    all_nodes: bool | None = Field(
        default=None,
        alias="allNodes",
        description="AllNodes indicates that all nodes have access to the device. Must only be set if Spec.PerDeviceNodeSelection is set to true. At most one of NodeName, NodeSelector and AllNodes can be set.",
    )
    allow_multiple_allocations: bool | None = Field(
        default=None,
        alias="allowMultipleAllocations",
        description="AllowMultipleAllocations marks whether the device is allowed to be allocated to multiple DeviceRequests. If AllowMultipleAllocations is set to true, the device can be allocated more than once, and all of its capacity is consumable, regardless of whether the requestPolicy is defined or not.",
    )
    attributes: dict[str, DeviceAttribute] | None = Field(
        default=None,
        alias="attributes",
        description="Attributes defines the set of attributes for this device. The name of each attribute must be unique in that set. The maximum number of attributes and capacities combined is 32.",
    )
    binding_conditions: list[str] | None = Field(
        default=None,
        alias="bindingConditions",
        description="BindingConditions defines the conditions for proceeding with binding. All of these conditions must be set in the per-device status conditions with a value of True to proceed with binding the pod to the node while scheduling the pod. The maximum number of binding conditions is 4. The conditions must be a valid condition type string. This is an alpha field and requires enabling the DRADeviceBindingConditions and DRAResourceClaimDeviceStatus feature gates.",
    )
    binding_failure_conditions: list[str] | None = Field(
        default=None,
        alias="bindingFailureConditions",
        description='BindingFailureConditions defines the conditions for binding failure. They may be set in the per-device status conditions. If any is set to "True", a binding failure occurred. The maximum number of binding failure conditions is 4. The conditions must be a valid condition type string. This is an alpha field and requires enabling the DRADeviceBindingConditions and DRAResourceClaimDeviceStatus feature gates.',
    )
    binds_to_node: bool | None = Field(
        default=None,
        alias="bindsToNode",
        description="BindsToNode indicates if the usage of an allocation involving this device has to be limited to exactly the node that was chosen when allocating the claim. If set to true, the scheduler will set the ResourceClaim.Status.Allocation.NodeSelector to match the node where the allocation was made. This is an alpha field and requires enabling the DRADeviceBindingConditions and DRAResourceClaimDeviceStatus feature gates.",
    )
    capacity: dict[str, DeviceCapacity] | None = Field(
        default=None,
        alias="capacity",
        description="Capacity defines the set of capacities for this device. The name of each capacity must be unique in that set. The maximum number of attributes and capacities combined is 32.",
    )
    consumes_counters: list[DeviceCounterConsumption] | None = Field(
        default=None,
        alias="consumesCounters",
        description="ConsumesCounters defines a list of references to sharedCounters and the set of counters that the device will consume from those counter sets. There can only be a single entry per counterSet. The maximum number of device counter consumptions per device is 2.",
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
        description="If specified, these are the driver-defined taints. The maximum number of taints is 16. If taints are set for any device in a ResourceSlice, then the maximum number of allowed devices per ResourceSlice is 64 instead of 128. This is an alpha field and requires enabling the DRADeviceTaints feature gate.",
    )
