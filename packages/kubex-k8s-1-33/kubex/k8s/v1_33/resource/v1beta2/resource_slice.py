from __future__ import annotations

from typing import ClassVar, Literal

from kubex.k8s.v1_33.resource.v1beta2.resource_slice_spec import ResourceSliceSpec
from kubex_core.models.interfaces import ClusterScopedEntity
from kubex_core.models.resource_config import ResourceConfig, Scope
from pydantic import Field


class ResourceSlice(ClusterScopedEntity):
    """ResourceSlice represents one or more resources in a pool of similar resources, managed by a common driver. A pool may span more than one ResourceSlice, and exactly how many ResourceSlices comprise a pool is determined by the driver. At the moment, the only supported resources are devices with attributes and capacities. Each device in a given pool, regardless of how many ResourceSlices, must have a unique name. The ResourceSlice in which a device gets published may change over time. The unique identifier for a device is the tuple <driver name>, <pool name>, <device name>. Whenever a driver needs to update a pool, it increments the pool.Spec.Pool.Generation number and updates all ResourceSlices with that new number and new resource definitions. A consumer must only use ResourceSlices with the highest generation number and ignore all others. When allocating all resources in a pool matching certain criteria or when looking for the best solution among several different alternatives, a consumer should check the number of ResourceSlices in a pool (included in each ResourceSlice) to determine whether its view of a pool is complete and if not, should wait until the driver has completed updating the pool. For resources that are not local to a node, the node name is not set. Instead, the driver may use a node selector to specify where the devices are available. This is an alpha type and requires enabling the DynamicResourceAllocation feature gate."""

    __RESOURCE_CONFIG__: ClassVar[ResourceConfig["ResourceSlice"]] = ResourceConfig[
        "ResourceSlice"
    ](
        version="v1beta2",
        kind="ResourceSlice",
        group="resource.k8s.io",
        plural="resourceslices",
        scope=Scope.CLUSTER,
    )
    api_version: Literal["resource.k8s.io/v1beta2"] = Field(
        default="resource.k8s.io/v1beta2",
        alias="apiVersion",
        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
    )
    kind: Literal["ResourceSlice"] = Field(
        default="ResourceSlice",
        alias="kind",
        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
    )
    spec: ResourceSliceSpec = Field(
        ...,
        alias="spec",
        description="Contains the information published by the driver. Changing the spec automatically increments the metadata.generation number.",
    )
